# -*- coding: utf-8 -*-

class Config:
    """开发环境配置"""
    
    # ==========================================
    # 数据库配置
    # ==========================================
    # 数据库类型: 'sqlite' 或 'mysql'
    DB_TYPE = 'sqlite'  # 默认使用SQLite
    
    # SQLite配置
    SQLITE_DB_PATH = '../data/yprompt.db'
    
    # MySQL配置 (如果使用MySQL，将DB_TYPE改为'mysql'并配置以下参数)
    DB_HOST = ''
    DB_USER = ''
    DB_PASS = ''
    DB_NAME = 'yprompt'
    DB_PORT = 3306
    
    # ==========================================
    # JWT配置
    # ==========================================
    SECRET_KEY = 'yprompt-secret-key-change-in-production'
    
    # ==========================================
    # Linux.do OAuth配置 (可选)
    # ==========================================
    # 如果需要Linux.do OAuth，请填写以下配置
    # 申请地址: https://linux.do
    LINUX_DO_CLIENT_ID = ''
    LINUX_DO_CLIENT_SECRET = ''
    LINUX_DO_REDIRECT_URI = 'http://localhost:5173/auth/callback'

    # ==========================================
    # 飞书 OAuth 配置 (可选)
    # ==========================================
    # 申请地址: https://open.feishu.cn/
    FEISHU_APP_ID = ''
    FEISHU_APP_SECRET = ''
    FEISHU_REDIRECT_URI = 'http://localhost:5173/auth/callback'

    # ==========================================
    # 默认管理员账号配置
    # ==========================================
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin123'
    DEFAULT_ADMIN_NAME = '管理员'
    
    # ==========================================
    # 注册功能配置
    # ==========================================
    # 是否允许本地用户注册（Linux.do OAuth不受此影响）
    REGISTRATION_ENABLED = True  # True=允许注册, False=禁止注册
    
    # ==========================================
    # 服务器配置
    # ==========================================
    DEBUG = True
    WORKERS = 1
    ACCESS_LOG = True
