#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据库适配器
使用 async SQLAlchemy 统一支持 SQLite 与 MySQL，提供原生 SQL 能力"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import quote_plus

from sanic.log import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


SqlParams = Union[Sequence[Any], Dict[str, Any], None]


class DatabaseAdapter(ABC):
    """数据库适配器基类"""

    @abstractmethod
    async def connect(self):
        """建立连接"""

    @abstractmethod
    async def close(self):
        """关闭连接"""

    @abstractmethod
    async def get(self, sql: str, params: SqlParams = None) -> Optional[Dict[str, Any]]:
        """查询单条记录"""

    @abstractmethod
    async def query(self, sql: str, params: SqlParams = None) -> List[Dict[str, Any]]:
        """查询多条记录"""

    @abstractmethod
    async def execute(self, sql: str, params: SqlParams = None) -> int:
        """执行SQL，返回影响行数"""

    @abstractmethod
    async def table_insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入数据并返回自增ID"""

    @abstractmethod
    async def table_update(self, table: str, data: Dict[str, Any], where: str):
        """更新数据"""

    @abstractmethod
    def transaction(self):
        """事务上下文"""


class SQLAlchemyAdapter(DatabaseAdapter):
    """基于 SQLAlchemy AsyncEngine 的通用适配器"""

    def __init__(self, db_url: str, *, connect_args: Optional[Dict[str, Any]] = None):
        self.db_url = db_url
        self.engine: AsyncEngine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            future=True,
            connect_args=connect_args or {},
        )

    async def connect(self):
        async with self.engine.connect() as conn:
            await conn.execute(text('SELECT 1'))

    async def close(self):
        await self.engine.dispose()

    async def get(self, sql: str, params: SqlParams = None) -> Optional[Dict[str, Any]]:
        sql_text, bind_params = self._prepare_sql(sql, params)
        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql_text), bind_params)
            row = result.mappings().first()
            return dict(row) if row else None

    async def query(self, sql: str, params: SqlParams = None) -> List[Dict[str, Any]]:
        sql_text, bind_params = self._prepare_sql(sql, params)
        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql_text), bind_params)
            return [dict(row) for row in result.mappings().all()]

    async def execute(self, sql: str, params: SqlParams = None) -> int:
        sql_text, bind_params = self._prepare_sql(sql, params)
        async with self.engine.begin() as conn:
            result = await conn.execute(text(sql_text), bind_params)
            return result.rowcount if result.rowcount is not None else 0

    async def table_insert(self, table: str, data: Dict[str, Any]) -> int:
        if not data:
            raise ValueError('table_insert 需要有效的数据字典')
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        sql_text, bind_params = self._prepare_sql(sql, list(data.values()))
        async with self.engine.begin() as conn:
            result = await conn.execute(text(sql_text), bind_params)
            last_id = result.lastrowid
            return int(last_id) if last_id is not None else 0

    async def table_update(self, table: str, data: Dict[str, Any], where: str):
        if not data:
            return
        set_clause = ', '.join([f"{column} = ?" for column in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = list(data.values())
        await self.execute(sql, params)

    def transaction(self):
        return self.engine.begin()

    @staticmethod
    def _prepare_sql(sql: str, params: SqlParams) -> Tuple[str, Dict[str, Any]]:
        if params is None:
            return sql, {}
        if isinstance(params, dict):
            return sql, params
        values = list(params)
        if not values:
            return sql, {}
        builder: List[str] = []
        bind: Dict[str, Any] = {}
        idx = 0
        for ch in sql:
            if ch == '?':
                key = f"p{idx}"
                if idx >= len(values):
                    raise ValueError('SQL参数个数不足')
                builder.append(f":{key}")
                bind[key] = values[idx]
                idx += 1
            else:
                builder.append(ch)
        if idx != len(values):
            raise ValueError('SQL参数个数过多')
        return ''.join(builder), bind


class SQLiteAdapter(SQLAlchemyAdapter):
    def __init__(self, db_path: str):
        self.db_path = os.path.abspath(db_path)
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        super().__init__(f"sqlite+aiosqlite:///{self.db_path}")


class MySQLAdapter(SQLAlchemyAdapter):
    def __init__(self, config: Dict[str, Any]):
        self.db_name = config.get('database')
        user = quote_plus(config.get('user', ''))
        password = quote_plus(config.get('password', '') or '')
        host = config.get('host', 'localhost')
        port = config.get('port', 3306)
        db_url = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{self.db_name}"
        super().__init__(db_url)


async def create_database_adapter(db_type: str, config: Dict[str, Any], app_config: Dict[str, Any] = None) -> DatabaseAdapter:
    if db_type == 'sqlite':
        adapter = SQLiteAdapter(config['path'])
        await adapter.connect()
        await _initialize_sqlite_if_needed(adapter, app_config)
        return adapter
    if db_type == 'mysql':
        adapter = MySQLAdapter(config)
        await adapter.connect()
        await _initialize_mysql_if_needed(adapter, config, app_config)
        return adapter
    raise ValueError(f"不支持的数据库类型: {db_type}")


async def _initialize_sqlite_if_needed(adapter: SQLiteAdapter, config: Dict[str, Any] = None):
    try:
        result = await adapter.get(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )

        if not result:
            logger.info('📦 SQLite数据库为空，开始初始化...')
            script_path = os.path.join(
                os.path.dirname(__file__),
                '../../migrations/init_sqlite.sql'
            )

            if os.path.exists(script_path):
                import aiosqlite

                async with aiosqlite.connect(adapter.db_path) as db:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        await db.executescript(f.read())
                        await db.commit()
                logger.info('✅ SQLite表结构初始化完成')
                await _create_default_admin(adapter, config)
            else:
                logger.warning(f"⚠️  未找到SQLite初始化脚本: {script_path}")
        else:
            logger.info('✅ SQLite数据库已存在，跳过表结构初始化')
            await _sync_admin_account(adapter, config)
    except Exception as exc:
        logger.error(f'❌ SQLite数据库初始化检查失败: {exc}')
        raise


async def _initialize_mysql_if_needed(adapter: MySQLAdapter, db_config: Dict[str, Any] = None, app_config: Dict[str, Any] = None):
    try:
        db_name = (db_config or {}).get('database') or (app_config or {}).get('DB_NAME')
        if not db_name:
            logger.warning('⚠️  未配置MySQL数据库名称，跳过初始化检查')
            return

        table_check_sql = """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = ? AND table_name = ?
            LIMIT 1
        """
        result = await adapter.get(table_check_sql, [db_name, 'users'])

        if not result:
            logger.info('📦 MySQL数据库为空，开始初始化...')
            await _execute_mysql_init_script(adapter)
            await _create_default_admin(adapter, app_config)
        else:
            logger.info('✅ MySQL数据库已存在，跳过表结构初始化')
            await _sync_admin_account(adapter, app_config)
    except Exception as exc:
        logger.exception(f'❌ MySQL数据库初始化检查失败: {exc}')
        raise


async def _execute_mysql_init_script(adapter: DatabaseAdapter):
    script_path = os.path.join(
        os.path.dirname(__file__),
        '../../migrations/init_mysql.sql'
    )

    if not os.path.exists(script_path):
        logger.warning(f"⚠️  未找到MySQL初始化脚本: {script_path}")
        return

    with open(script_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    statements = _split_sql_statements(sql_script)

    for statement in statements:
        try:
            await adapter.execute(statement)
        except Exception as exc:
            logger.error(f'❌ 执行MySQL初始化语句失败: {exc} | SQL: {statement}')
            raise

    logger.info('✅ MySQL表结构初始化完成')


def _split_sql_statements(sql_script: str) -> List[str]:
    statements: List[str] = []
    buffer: List[str] = []

    for line in sql_script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            continue
        buffer.append(line)
        if stripped.endswith(';'):
            statement = '\n'.join(buffer).strip()
            if statement.endswith(';'):
                statement = statement[:-1]
            if statement:
                statements.append(statement)
            buffer = []

    if buffer:
        statement = '\n'.join(buffer).strip()
        if statement.endswith(';'):
            statement = statement[:-1]
        if statement:
            statements.append(statement)

    return statements


async def _create_default_admin(adapter: DatabaseAdapter, config: Dict[str, Any] = None):
    try:
        admin_username = 'admin'
        admin_password = 'admin123'
        admin_name = '管理员'

        if config:
            admin_username = config.get('DEFAULT_ADMIN_USERNAME', 'admin')
            admin_password = config.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
            admin_name = config.get('DEFAULT_ADMIN_NAME', '管理员')

        existing_admin = await adapter.get(
            "SELECT id FROM users WHERE username = ? AND auth_type = 'local'",
            [admin_username]
        )

        if existing_admin:
            logger.info(f"✅ 管理员账号已存在: {admin_username}")
            return

        import bcrypt

        password_bytes = admin_password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

        await adapter.execute(
            """
            INSERT INTO users (username, password_hash, name, auth_type, is_admin, is_active)
            VALUES (?, ?, ?, 'local', 1, 1)
            """,
            [admin_username, password_hash, admin_name]
        )
        logger.info(f"✅ 默认管理员账号创建成功: {admin_username} / {admin_password}")
    except Exception as exc:
        logger.error(f'❌ 创建默认管理员账号失败: {exc}')
        raise


async def _sync_admin_account(adapter: DatabaseAdapter, config: Dict[str, Any] = None):
    try:
        admin_username = 'admin'
        admin_password = 'admin123'
        admin_name = '管理员'

        if config:
            admin_username = config.get('DEFAULT_ADMIN_USERNAME', 'admin')
            admin_password = config.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
            admin_name = config.get('DEFAULT_ADMIN_NAME', '管理员')

        import bcrypt

        password_bytes = admin_password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

        existing_admin = await adapter.get(
            "SELECT id, password_hash FROM users WHERE username = ? AND auth_type = 'local'",
            [admin_username]
        )

        if existing_admin:
            old_hash = existing_admin.get('password_hash', '') or ''
            try:
                is_password_correct = bcrypt.checkpw(password_bytes, old_hash.encode('utf-8'))
            except Exception:
                is_password_correct = False

            if not is_password_correct:
                await adapter.execute(
                    "UPDATE users SET password_hash = ?, name = ? WHERE id = ?",
                    [password_hash, admin_name, existing_admin['id']]
                )
                logger.info(f"🔄 管理员账号密码已更新: {admin_username}")
            else:
                logger.info(f"✅ 管理员账号配置正确: {admin_username}")
        else:
            await adapter.execute(
                """
                INSERT INTO users (username, password_hash, name, auth_type, is_admin, is_active)
                VALUES (?, ?, ?, 'local', 1, 1)
                """,
                [admin_username, password_hash, admin_name]
            )
            logger.info(f"✅ 管理员账号创建成功: {admin_username} / {admin_password}")
    except Exception as exc:
        logger.error(f'❌ 同步管理员账号失败: {exc}')
        raise
