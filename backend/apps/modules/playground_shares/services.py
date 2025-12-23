"""操练场分享服务"""
import datetime
import json
import secrets
from typing import Any, Dict, List, Optional

from sanic.log import logger

from apps.utils.password_utils import PasswordUtil

MAX_PAYLOAD_BYTES = 1024 * 1024  # 1MB
ALLOWED_ACCESS_MODES = {'public', 'auth_only'}


class PlaygroundShareService:
    def __init__(self, db):
        self.db = db

    async def create_share(self, user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        messages = payload.get('messages') or []
        if not isinstance(messages, list) or len(messages) == 0:
            raise ValueError('请至少提供一条消息')

        for msg in messages:
            if msg.get('attachments'):
                raise ValueError('分享暂不支持包含附件的消息，请先移除附件')

        provider = payload.get('provider') or {}
        required_provider_fields = ['id', 'name', 'modelId', 'modelName']
        if not all(provider.get(field) for field in required_provider_fields):
            raise ValueError('提供商信息不完整')

        artifact = payload.get('artifact')
        if artifact:
            if not artifact.get('type') or artifact.get('content') is None:
                raise ValueError('artifact 信息不完整')

        system_prompt = payload.get('systemPrompt', '') or ''
        title = payload.get('title') or '提示词操练场快照'
        title = title.strip()[:200]

        access_mode = (payload.get('access_mode') or 'public').lower()
        if access_mode not in ALLOWED_ACCESS_MODES:
            raise ValueError('访问模式无效')

        is_permanent = bool(payload.get('is_permanent'))
        expires_at = None
        if not is_permanent:
            expires_str = payload.get('expires_at')
            if not expires_str:
                raise ValueError('请传入自定义到期时间或选择永久有效')
            expires_at = self._parse_datetime(expires_str)
            if expires_at <= datetime.datetime.now():
                raise ValueError('到期时间必须晚于当前时间')

        password = payload.get('password')
        password_hash = None
        if password:
            password = password.strip()
            if len(password) < 4 or len(password) > 128:
                raise ValueError('密码长度需在4-128个字符之间')
            password_hash = PasswordUtil.hash_password(password)

        provider_json = json.dumps(provider, ensure_ascii=False)
        messages_json = json.dumps(messages, ensure_ascii=False)

        artifact_type = artifact.get('type') if artifact else None
        artifact_content = artifact.get('content') if artifact else None
        artifact_json = json.dumps(artifact, ensure_ascii=False) if artifact else ''

        estimated_size = len(provider_json.encode('utf-8')) + len(messages_json.encode('utf-8'))
        estimated_size += len((system_prompt or '').encode('utf-8'))
        estimated_size += len((artifact_json or '').encode('utf-8'))
        if estimated_size > MAX_PAYLOAD_BYTES:
            raise ValueError('分享内容过大，请精简对话或输出内容')

        share_code = await self._generate_unique_code()
        expires_value = expires_at.strftime('%Y-%m-%d %H:%M:%S') if expires_at else None

        # 可选：关联提示词ID（从详情页演练时传入）
        prompt_id = payload.get('prompt_id')

        fields = {
            'user_id': user_id,
            'prompt_id': prompt_id,  # 关联提示词
            'share_code': share_code,
            'title': title,
            'system_prompt': system_prompt,
            'provider_snapshot': provider_json,
            'artifact_type': artifact_type,
            'artifact_content': artifact_content,
            'messages_json': messages_json,
            'is_permanent': 1 if is_permanent else 0,
            'expires_at': expires_value,
            'access_mode': access_mode,
            'password_hash': password_hash,
            'is_active': 1
        }

        await self.db.table_insert('playground_shares', fields)
        logger.info(f'✅ 操练场分享创建成功: user_id={user_id}, share_code={share_code}')
        return {
            'share_code': share_code,
            'share_path': f'/playground/share/{share_code}'
        }

    async def list_shares(self, user_id: int, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        offset = (page - 1) * limit if page > 0 else 0
        total_sql = 'SELECT COUNT(*) as total FROM playground_shares WHERE user_id = ?'
        total_row = await self.db.get(total_sql, [user_id])
        total = total_row['total'] if total_row else 0

        query = (
            "SELECT share_code, title, access_mode, is_permanent, expires_at, view_count, "
            "password_hash, is_active, create_time "
            "FROM playground_shares WHERE user_id = ? ORDER BY create_time DESC LIMIT ? OFFSET ?"
        )
        rows = await self.db.query(query, [user_id, limit, offset])
        items = []
        for row in rows:
            normalized = self._serialize_row(row)
            items.append({
                'share_code': normalized.get('share_code'),
                'title': normalized.get('title'),
                'access_mode': normalized.get('access_mode'),
                'is_permanent': bool(normalized.get('is_permanent')),
                'expires_at': normalized.get('expires_at'),
                'view_count': normalized.get('view_count', 0),
                'has_password': bool(normalized.get('password_hash')),
                'is_active': bool(normalized.get('is_active', 1)),
                'create_time': normalized.get('create_time')
            })
        return {
            'total': total,
            'page': page,
            'limit': limit,
            'items': items
        }

    async def get_share_for_viewer(self, share_code: str) -> Optional[Dict[str, Any]]:
        sql = (
            "SELECT ps.*, u.name as owner_name, u.avatar as owner_avatar, u.id as owner_id "
            "FROM playground_shares ps JOIN users u ON ps.user_id = u.id "
            "WHERE ps.share_code = ?"
        )
        result = await self.db.get(sql, [share_code])
        return self._serialize_row(result) if result else None

    async def record_view(self, share_id: int):
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        update_sql = (
            "UPDATE playground_shares SET view_count = view_count + 1, last_access_time = ? "
            "WHERE id = ?"
        )
        await self.db.execute(update_sql, [now_str, share_id])

    async def delete_share(self, user_id: int, share_code: str) -> bool:
        """物理删除分享记录"""
        sql = "DELETE FROM playground_shares WHERE user_id = ? AND share_code = ?"
        await self.db.execute(sql, [user_id, share_code])
        logger.info(f'✅ 删除操练场分享: user_id={user_id}, share_code={share_code}')
        return True

    async def update_share(self, user_id: int, share_code: str, payload: Dict[str, Any]) -> bool:
        existing = await self.db.get(
            "SELECT id FROM playground_shares WHERE user_id = ? AND share_code = ?",
            [user_id, share_code]
        )
        if not existing:
            raise ValueError('分享不存在或无权限修改')

        fields = {}

        if 'title' in payload:
            title = (payload.get('title') or '').strip()[:200]
            fields['title'] = title or '提示词操练场快照'

        if 'access_mode' in payload:
            access_mode = (payload.get('access_mode') or '').lower()
            if access_mode not in ALLOWED_ACCESS_MODES:
                raise ValueError('访问模式无效')
            fields['access_mode'] = access_mode

        if 'is_permanent' in payload:
            is_perm = bool(payload.get('is_permanent'))
            fields['is_permanent'] = 1 if is_perm else 0
            if not is_perm:
                expires_at = payload.get('expires_at')
                if not expires_at:
                    raise ValueError('请提供到期时间')
                expires_dt = self._parse_datetime(expires_at)
                if expires_dt <= datetime.datetime.now():
                    raise ValueError('到期时间必须晚于当前时间')
                fields['expires_at'] = expires_dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                fields['expires_at'] = None
        elif 'expires_at' in payload:
            expires_dt = self._parse_datetime(payload.get('expires_at'))
            if expires_dt <= datetime.datetime.now():
                raise ValueError('到期时间必须晚于当前时间')
            fields['expires_at'] = expires_dt.strftime('%Y-%m-%d %H:%M:%S')

        if payload.get('remove_password'):
            fields['password_hash'] = None
        elif 'password' in payload and payload.get('password'):
            new_pwd = payload.get('password').strip()
            if len(new_pwd) < 4 or len(new_pwd) > 128:
                raise ValueError('密码长度需在4-128个字符之间')
            fields['password_hash'] = PasswordUtil.hash_password(new_pwd)

        if not fields:
            return True

        sets = ', '.join([f"{key} = ?" for key in fields.keys()])
        sql = f"UPDATE playground_shares SET {sets} WHERE user_id = ? AND share_code = ?"
        params = list(fields.values()) + [user_id, share_code]
        await self.db.execute(sql, params)
        return True

    async def _generate_unique_code(self, length: int = 12) -> str:
        while True:
            code = secrets.token_urlsafe(length)[:length]
            existing = await self.db.get(
                "SELECT id FROM playground_shares WHERE share_code = ?",
                [code]
            )
            if not existing:
                return code

    @staticmethod
    def _parse_datetime(value: str) -> datetime.datetime:
        if not value:
            raise ValueError('到期时间不能为空')
        value = value.strip()
        try:
            if value.endswith('Z'):
                value = value[:-1]
            return datetime.datetime.fromisoformat(value.replace('T', ' '))
        except Exception as exc:
            raise ValueError('到期时间格式不正确') from exc

    @staticmethod
    def _serialize_row(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not row:
            return {}
        serialized: Dict[str, Any] = {}
        for key, value in dict(row).items():
            if isinstance(value, datetime.datetime):
                serialized[key] = value.isoformat(sep=' ', timespec='seconds')
            else:
                serialized[key] = value
        return serialized
