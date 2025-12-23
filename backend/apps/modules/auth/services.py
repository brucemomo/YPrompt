"""
认证服务类
处理用户认证相关的业务逻辑
支持: Linux.do OAuth + 飞书 OAuth + 本地用户名密码认证
"""
import datetime
from sanic.log import logger
from apps.utils.password_utils import PasswordUtil


class AuthService:
    """认证服务类"""
    
    def __init__(self, db):
        """
        初始化认证服务
        
        Args:
            db: 数据库连接对象(ezmysql ConnectionAsync)
        """
        self.db = db
    
    async def create_or_update_user_from_linux_do(self, user_info):
        """
        从Linux.do用户信息创建或更新用户
        
        Args:
            user_info: Linux.do用户信息字典,包含:
                - id: Linux.do用户ID (唯一标识)
                - username: 论坛用户名
                - name: 论坛用户昵称
                - avatar_template: 用户头像模板URL
                - active: 账号活跃状态
                - trust_level: 信任等级 (0-4)
                
        Returns:
            dict: 用户信息
        """
        linux_do_id = str(user_info.get('id'))
        
        if not linux_do_id:
            raise ValueError('用户信息中缺少id字段')
        
        try:
            # 1. 查询用户是否存在
            sql = "SELECT * FROM users WHERE linux_do_id = ?"
            user = await self.db.get(sql, [linux_do_id])
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 处理头像URL (支持多种尺寸)
            avatar_template = user_info.get('avatar_template', '')
            avatar = avatar_template.replace('{size}', '240') if avatar_template and '{size}' in avatar_template else avatar_template
            
            # 确保 name 字段不为空：优先使用 name，其次 username，最后使用 linux_do_username
            name = user_info.get('name') or user_info.get('username') or user_info.get('linux_do_username', '未知用户')
            linux_do_username = user_info.get('username', '')
            
            if user:
                # 2. 用户存在,更新用户信息和登录时间（使用参数化查询）
                update_sql = """
                    UPDATE users SET 
                        name = ?,
                        linux_do_username = ?,
                        avatar = ?,
                        auth_type = 'linux_do',
                        last_login_time = ?
                    WHERE linux_do_id = ?
                """
                
                await self.db.execute(update_sql, [name, linux_do_username, avatar, current_time, linux_do_id])
                
                # 重新查询用户信息
                sql = "SELECT * FROM users WHERE linux_do_id = ?"
                return await self.db.get(sql, [linux_do_id])
            else:
                # 3. 用户不存在,创建新用户
                # 确保 name 字段不为空：优先使用 name，其次 username，最后使用 linux_do_username
                name = user_info.get('name') or user_info.get('username') or user_info.get('linux_do_username', '未知用户')
                
                fields = {
                    'linux_do_id': linux_do_id,
                    'linux_do_username': user_info.get('username', ''),
                    'name': name,
                    'avatar': avatar,
                    'auth_type': 'linux_do',
                    'is_active': 1 if user_info.get('active', True) else 0,
                    'last_login_time': current_time
                }
                
                user_id = await self.db.table_insert('users', fields)
                
                return await self.get_user_by_id(user_id)
                
        except Exception as e:
            logger.error(f'❌ 创建或更新Linux.do用户失败: {e}')
            raise

    async def create_or_update_user_from_feishu(self, user_info):
        """
        从飞书用户信息创建或更新用户
        """
        feishu_open_id = user_info.get('open_id')
        
        if not feishu_open_id:
            raise ValueError('用户信息中缺少open_id')
        
        try:
            sql = "SELECT * FROM users WHERE feishu_open_id = ?"
            user = await self.db.get(sql, [feishu_open_id])
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            avatar = user_info.get('avatar_640') or user_info.get('avatar_240') or user_info.get('avatar_72') or ''
            name = user_info.get('name') or '飞书用户'
            email = user_info.get('email') or user_info.get('enterprise_email', '')
            feishu_union_id = user_info.get('union_id') or ''
            
            if user:
                update_sql = """
                    UPDATE users SET
                        name = ?,
                        avatar = ?,
                        email = ?,
                        feishu_union_id = ?,
                        auth_type = 'feishu',
                        last_login_time = ?
                    WHERE feishu_open_id = ?
                """
                await self.db.execute(update_sql, [
                    name,
                    avatar,
                    email,
                    feishu_union_id,
                    current_time,
                    feishu_open_id
                ])
                
                sql = "SELECT * FROM users WHERE feishu_open_id = ?"
                return await self.db.get(sql, [feishu_open_id])
            else:
                fields = {
                    'feishu_open_id': feishu_open_id,
                    'feishu_union_id': feishu_union_id,
                    'name': name,
                    'avatar': avatar,
                    'email': email,
                    'auth_type': 'feishu',
                    'is_active': 1,
                    'last_login_time': current_time
                }
                
                user_id = await self.db.table_insert('users', fields)
                return await self.get_user_by_id(user_id)
        except Exception as e:
            logger.error(f'❌ 创建或更新飞书用户失败: {e}')
            raise
    
    async def get_user_by_id(self, user_id):
        """
        根据ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 用户信息,不存在返回None
        """
        try:
            sql = "SELECT * FROM users WHERE id = ?"
            user = await self.db.get(sql, [user_id])
            
            # 移除敏感字段
            if user and 'password_hash' in user:
                user = dict(user)
                del user['password_hash']
            
            return user
            
        except Exception as e:
            logger.error(f'❌ 查询用户失败: {e}')
            raise
    
    async def create_local_user(self, username, password, name=None):
        """
        创建本地用户(用户名密码认证)
        
        Args:
            username: 用户名
            password: 明文密码
            name: 显示名称(可选,默认使用用户名)
            
        Returns:
            dict: 用户信息
        """
        try:
            # 1. 检查用户名是否已存在
            sql = "SELECT * FROM users WHERE username = ?"
            existing_user = await self.db.get(sql, [username])
            
            if existing_user:
                raise ValueError(f'用户名 {username} 已存在')
            
            # 2. 密码哈希
            password_hash = PasswordUtil.hash_password(password)
            
            # 3. 创建用户
            # 确保 name 字段不为空：如果未提供 name，使用 username 作为默认值
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            fields = {
                'username': username,
                'password_hash': password_hash,
                'name': name if name else username,  # 默认使用 username
                'auth_type': 'local',
                'is_active': 1,
                'last_login_time': current_time
            }
            
            user_id = await self.db.table_insert('users', fields)
            
            logger.info(f'✅ 本地用户创建成功: username={username}, id={user_id}')
            
            return await self.get_user_by_id(user_id)
            
        except Exception as e:
            logger.error(f'❌ 创建本地用户失败: {e}')
            raise
    
    async def verify_local_user(self, username, password):
        """
        验证本地用户密码
        
        Args:
            username: 用户名
            password: 明文密码
            
        Returns:
            dict: 用户信息(验证成功) 或 None(验证失败)
        """
        try:
            # 1. 查询用户
            sql = "SELECT * FROM users WHERE username = ? AND auth_type = 'local'"
            user = await self.db.get(sql, [username])
            
            if not user:
                logger.warning(f'⚠️  用户不存在: username={username}')
                return None
            
            # 2. 检查用户是否激活
            if not user.get('is_active', 0):
                logger.warning(f'⚠️  用户已被禁用: username={username}')
                return None
            
            # 3. 验证密码
            password_hash = user.get('password_hash')
            if not PasswordUtil.verify_password(password, password_hash):
                logger.warning(f'⚠️  密码错误: username={username}')
                return None
            
            # 4. 更新最后登录时间
            await self.update_last_login_time(user['id'])
            
            logger.info(f'✅ 本地用户登录成功: username={username}, id={user["id"]}')
            
            return user
            
        except Exception as e:
            logger.error(f'❌ 验证本地用户失败: {e}')
            return None
    
    async def get_user_by_linux_do_id(self, linux_do_id):
        """
        根据linux_do_id获取用户
        
        Args:
            linux_do_id: Linux.do用户ID
            
        Returns:
            dict: 用户信息,不存在返回None
        """
        try:
            sql = "SELECT * FROM users WHERE linux_do_id = ?"
            user = await self.db.get(sql, [linux_do_id])
            
            return user
            
        except Exception as e:
            logger.error(f'❌ 查询用户失败: {e}')
            raise
    
    async def get_user_by_username(self, username):
        """
        根据username获取用户
        
        Args:
            username: 用户名
            
        Returns:
            dict: 用户信息,不存在返回None
        """
        try:
            sql = "SELECT * FROM users WHERE username = ?"
            user = await self.db.get(sql, [username])
            
            return user
            
        except Exception as e:
            logger.error(f'❌ 查询用户失败: {e}')
            raise

    async def get_user_by_feishu_open_id(self, feishu_open_id):
        """
        根据飞书open_id获取用户
        """
        try:
            sql = "SELECT * FROM users WHERE feishu_open_id = ?"
            return await self.db.get(sql, [feishu_open_id])
        except Exception as e:
            logger.error(f'❌ 查询飞书用户失败: {e}')
            raise
    
    async def update_last_login_time(self, user_id):
        """
        更新用户最后登录时间
        
        Args:
            user_id: 用户ID
        """
        try:
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sql = f"UPDATE users SET last_login_time = '{current_time}' WHERE id = {user_id}"
            await self.db.execute(sql)
            
        except Exception as e:
            logger.error(f'❌ 更新登录时间失败: {e}')
            # 不抛出异常,因为这不是关键操作
    
    async def deactivate_user(self, user_id):
        """
        禁用用户
        
        Args:
            user_id: 用户ID
        """
        try:
            sql = f"UPDATE users SET is_active = 0 WHERE id = {user_id}"
            await self.db.execute(sql)
            
        except Exception as e:
            logger.error(f'❌ 禁用用户失败: {e}')
            raise
    
    async def activate_user(self, user_id):
        """
        激活用户
        
        Args:
            user_id: 用户ID
        """
        try:
            sql = f"UPDATE users SET is_active = 1 WHERE id = {user_id}"
            await self.db.execute(sql)
            
        except Exception as e:
            logger.error(f'❌ 激活用户失败: {e}')
            raise
