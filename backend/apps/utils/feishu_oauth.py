#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书 OAuth 2.0 工具
封装授权码登录流程：获取tenant_access_token -> 交换用户code -> 获取用户信息
"""

import time
import requests
from sanic.log import logger
from config.settings import Config


class FeishuOAuth:
    """飞书 OAuth2.0 认证工具"""
    
    AUTH_URL = 'https://accounts.feishu.cn/open-apis/authen/v1/authorize'
    TENANT_TOKEN_URL = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    ACCESS_TOKEN_URL = 'https://open.feishu.cn/open-apis/authen/v1/access_token'
    USER_INFO_URL_TEMPLATE = 'https://open.feishu.cn/open-apis/contact/v3/users/{open_id}?user_id_type=open_id'
    DEFAULT_SCOPE = 'contact:contact.base:readonly'
    
    def __init__(self):
        self.app_id = Config.FEISHU_APP_ID
        self.app_secret = Config.FEISHU_APP_SECRET
        self.redirect_uri = Config.FEISHU_REDIRECT_URI
        self._tenant_access_token = None
        self._tenant_token_expire_at = 0
        
        if not self.is_configured():
            logger.warning('⚠️  飞书 OAuth 未完整配置，登录将不可用')
    
    @staticmethod
    def is_configured():
        """检查飞书 OAuth 是否配置"""
        return all([
            getattr(Config, 'FEISHU_APP_ID', ''),
            getattr(Config, 'FEISHU_APP_SECRET', ''),
            getattr(Config, 'FEISHU_REDIRECT_URI', '')
        ])
    
    def get_authorization_url(self, state=None, redirect_uri=None, scope=None):
        """
        构建授权URL
        Args:
            state: CSRF防护参数
            redirect_uri: 回调地址（默认读取配置）
            scope: 授权范围
        """
        if not self.is_configured():
            raise ValueError('飞书 OAuth 未配置')
        
        params = {
            'app_id': self.app_id,
            'redirect_uri': redirect_uri or self.redirect_uri,
            'response_type': 'code',
            'scope': scope or self.DEFAULT_SCOPE
        }
        if state:
            params['state'] = state
        
        query = '&'.join(f'{k}={requests.utils.quote(str(v), safe="")}' for k, v in params.items() if v)
        return f'{self.AUTH_URL}?{query}'
    
    def _get_tenant_access_token(self, force_refresh=False):
        """获取（或复用）tenant_access_token"""
        if not self.is_configured():
            raise ValueError('飞书 OAuth 未配置')
        
        now = time.time()
        if not force_refresh and self._tenant_access_token and now < self._tenant_token_expire_at:
            return self._tenant_access_token
        
        payload = {
            'app_id': self.app_id,
            'app_secret': self.app_secret
        }
        
        try:
            response = requests.post(
                self.TENANT_TOKEN_URL,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0:
                raise ValueError(data.get('msg', 'tenant_access_token获取失败'))
            
            token = data.get('tenant_access_token')
            expire = data.get('expire', 3600)
            self._tenant_access_token = token
            self._tenant_token_expire_at = now + expire - 30  # 提前30秒刷新
            
            logger.info('✅ 成功获取飞书 tenant_access_token')
            return token
        except Exception as exc:
            logger.error(f'❌ 获取飞书 tenant_access_token 失败: {exc}')
            raise
    
    def _exchange_code(self, code):
        """通过授权码获取用户access_token和open_id"""
        tenant_token = self._get_tenant_access_token()
        headers = {
            'Authorization': f'Bearer {tenant_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'grant_type': 'authorization_code',
            'code': code
        }
        
        try:
            response = requests.post(
                self.ACCESS_TOKEN_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            if data.get('code') != 0:
                raise ValueError(data.get('msg', '获取用户access_token失败'))
            
            return data.get('data', {})
        except Exception as exc:
            logger.error(f'❌ 交换飞书授权码失败: {exc}')
            raise
    
    def _get_user_profile(self, open_id):
        """使用tenant_access_token获取用户信息"""
        tenant_token = self._get_tenant_access_token()
        headers = {
            'Authorization': f'Bearer {tenant_token}',
            'Content-Type': 'application/json'
        }
        url = self.USER_INFO_URL_TEMPLATE.format(open_id=open_id)
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0:
                raise ValueError(data.get('msg', '获取用户信息失败'))
            
            user = data.get('data', {}).get('user', {})
            avatar = user.get('avatar', {}) or {}
            
            return {
                'open_id': user.get('open_id'),
                'union_id': user.get('union_id'),
                'name': user.get('name') or user.get('en_name') or '',
                'avatar_72': avatar.get('avatar_72', ''),
                'avatar_240': avatar.get('avatar_240', ''),
                'avatar_640': avatar.get('avatar_640', ''),
                'email': user.get('email', ''),
                'mobile': user.get('mobile', ''),
                'enterprise_email': user.get('enterprise_email', ''),
                'user_id': user.get('user_id'),
                'tenant_key': user.get('tenant_key'),
            }
        except Exception as exc:
            logger.error(f'❌ 获取飞书用户信息失败: {exc}')
            raise
    
    def get_user_by_code(self, code):
        """通过授权码获取完整的飞书用户信息"""
        if not code:
            raise ValueError('缺少授权码')
        
        access_data = self._exchange_code(code)
        open_id = access_data.get('open_id')
        if not open_id:
            raise ValueError('飞书返回数据缺少open_id')
        
        profile = self._get_user_profile(open_id)
        profile.update({
            'access_token': access_data.get('access_token'),
            'refresh_token': access_data.get('refresh_token'),
            'expires_in': access_data.get('expires_in'),
            'token_type': access_data.get('token_type'),
            'scope': access_data.get('scope'),
            'tenant_key': access_data.get('tenant_key') or profile.get('tenant_key')
        })
        return profile
