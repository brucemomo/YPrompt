# -*- coding: utf-8 -*-
"""社区功能业务逻辑"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sanic.log import logger


class CommunityService:
    def __init__(self, db):
        self.db = db
    
    async def get_public_prompts(self, page: int = 1, limit: int = 20, 
                                  sort: str = 'hot', tag: str = None, 
                                  keyword: str = None, current_user_id: int = None) -> Dict[str, Any]:
        """获取公开提示词列表"""
        try:
            offset = (page - 1) * limit
            
            # 构建查询条件
            where_clauses = ['p.is_public = 1']
            params = []
            
            if tag:
                where_clauses.append('(p.tags LIKE ? OR p.tags LIKE ? OR p.tags LIKE ?)')
                params.extend([f'{tag},%', f'%,{tag},%', f'%,{tag}'])
            
            if keyword:
                where_clauses.append('(p.title LIKE ? OR p.description LIKE ?)')
                search_term = f'%{keyword}%'
                params.extend([search_term, search_term])
            
            where_sql = ' AND '.join(where_clauses)
            
            # 排序逻辑
            if sort == 'latest':
                order_sql = 'ORDER BY p.create_time DESC'
            else:  # hot
                # 热度算法: 按hot_score排序
                order_sql = 'ORDER BY p.hot_score DESC, p.create_time DESC'
            
            # 统计总数
            count_sql = f'SELECT COUNT(*) as total FROM prompts p WHERE {where_sql}'
            total_row = await self.db.get(count_sql, params)
            total = total_row['total'] if total_row else 0
            
            # 查询列表
            query_sql = f"""
                SELECT 
                    p.id, p.title, p.description, p.final_prompt,
                    p.prompt_type, p.language, p.format, p.tags,
                    p.user_id, u.name as author_name, u.avatar as author_avatar,
                    p.view_count, p.use_count, p.like_count, p.comment_count, p.hot_score,
                    p.create_time, p.update_time
                FROM prompts p
                LEFT JOIN users u ON p.user_id = u.id
                WHERE {where_sql}
                {order_sql}
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            rows = await self.db.query(query_sql, params)
            
            # 查询当前用户的点赞状态
            items = []
            for row in rows:
                item = self._serialize_row(row)
                item['is_liked'] = False
                
                if current_user_id:
                    like_sql = 'SELECT id FROM prompt_likes WHERE prompt_id = ? AND user_id = ?'
                    like_row = await self.db.get(like_sql, [row['id'], current_user_id])
                    item['is_liked'] = bool(like_row)
                
                items.append(item)
            
            return {
                'total': total,
                'page': page,
                'limit': limit,
                'items': items
            }
        except Exception as exc:
            logger.error(f'❌ 获取公开提示词列表失败: {exc}')
            raise
    
    async def get_prompt_detail(self, prompt_id: int, current_user_id: int = None) -> Optional[Dict[str, Any]]:
        """获取提示词详情"""
        try:
            sql = """
                SELECT 
                    p.*,
                    u.name as author_name, u.avatar as author_avatar
                FROM prompts p
                LEFT JOIN users u ON p.user_id = u.id
                WHERE p.id = ? AND p.is_public = 1
            """
            prompt = await self.db.get(sql, [prompt_id])
            
            if not prompt:
                return None
            
            # 增加浏览次数
            await self.increment_view_count(prompt_id)
            prompt['view_count'] = (prompt.get('view_count') or 0) + 1
            
            # 记录访问足迹（如果用户已登录）
            if current_user_id:
                await self.record_visit(prompt_id, current_user_id)
            
            # 查询点赞状态
            prompt['is_liked'] = False
            if current_user_id:
                like_sql = 'SELECT id FROM prompt_likes WHERE prompt_id = ? AND user_id = ?'
                like_row = await self.db.get(like_sql, [prompt_id, current_user_id])
                prompt['is_liked'] = bool(like_row)
            
            return self._serialize_row(prompt)
        except Exception as exc:
            logger.error(f'❌ 获取提示词详情失败: {exc}')
            raise
    
    async def increment_view_count(self, prompt_id: int):
        """增加浏览次数"""
        try:
            sql = 'UPDATE prompts SET view_count = view_count + 1 WHERE id = ?'
            await self.db.execute(sql, [prompt_id])
        except Exception as exc:
            logger.error(f'❌ 增加浏览次数失败: {exc}')
    
    async def toggle_like(self, prompt_id: int, user_id: int) -> Dict[str, Any]:
        """切换点赞状态"""
        try:
            # 检查是否已点赞
            check_sql = 'SELECT id FROM prompt_likes WHERE prompt_id = ? AND user_id = ?'
            existing = await self.db.get(check_sql, [prompt_id, user_id])
            
            if existing:
                # 取消点赞
                delete_sql = 'DELETE FROM prompt_likes WHERE prompt_id = ? AND user_id = ?'
                await self.db.execute(delete_sql, [prompt_id, user_id])
                
                # 减少计数（SQLite兼容写法：使用CASE防止负数）
                update_sql = '''
                    UPDATE prompts 
                    SET like_count = CASE 
                        WHEN like_count > 0 THEN like_count - 1 
                        ELSE 0 
                    END 
                    WHERE id = ?
                '''
                await self.db.execute(update_sql, [prompt_id])
                
                is_liked = False
                action = 'unliked'
            else:
                # 添加点赞
                insert_sql = 'INSERT INTO prompt_likes (prompt_id, user_id) VALUES (?, ?)'
                await self.db.execute(insert_sql, [prompt_id, user_id])
                
                # 增加计数
                update_sql = 'UPDATE prompts SET like_count = like_count + 1 WHERE id = ?'
                await self.db.execute(update_sql, [prompt_id])
                
                is_liked = True
                action = 'liked'
            
            # 更新热度分数
            await self.update_hot_score(prompt_id)
            
            # 获取最新计数
            count_sql = 'SELECT like_count FROM prompts WHERE id = ?'
            count_row = await self.db.get(count_sql, [prompt_id])
            like_count = count_row['like_count'] if count_row else 0
            
            return {
                'is_liked': is_liked,
                'like_count': like_count,
                'action': action
            }
        except Exception as exc:
            logger.error(f'❌ 切换点赞状态失败: {exc}')
            raise
    
    async def update_hot_score(self, prompt_id: int):
        """更新热度分数"""
        try:
            # 热度算法: (view_count * 0.1) + (use_count * 1.0) + (like_count * 2.0) + (comment_count * 5.0)
            sql = """
                UPDATE prompts 
                SET hot_score = (view_count * 0.1) + (use_count * 1.0) + (like_count * 2.0) + (comment_count * 5.0)
                WHERE id = ?
            """
            await self.db.execute(sql, [prompt_id])
        except Exception as exc:
            logger.error(f'❌ 更新热度分数失败: {exc}')
    
    async def get_comments(self, prompt_id: int, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """获取评论列表"""
        try:
            offset = (page - 1) * limit
            
            # 统计总数
            count_sql = 'SELECT COUNT(*) as total FROM prompt_comments WHERE prompt_id = ? AND is_deleted = 0'
            total_row = await self.db.get(count_sql, [prompt_id])
            total = total_row['total'] if total_row else 0
            
            # 查询评论列表
            query_sql = """
                SELECT 
                    c.id, c.prompt_id, c.user_id, c.parent_id, c.content, c.is_edited,
                    c.create_time, c.update_time,
                    u.name as user_name, u.avatar as user_avatar,
                    pu.name as parent_user_name
                FROM prompt_comments c
                LEFT JOIN users u ON c.user_id = u.id
                LEFT JOIN prompt_comments pc ON c.parent_id = pc.id
                LEFT JOIN users pu ON pc.user_id = pu.id
                WHERE c.prompt_id = ? AND c.is_deleted = 0
                ORDER BY c.create_time ASC
                LIMIT ? OFFSET ?
            """
            rows = await self.db.query(query_sql, [prompt_id, limit, offset])
            
            return {
                'total': total,
                'page': page,
                'limit': limit,
                'items': [self._serialize_row(row) for row in rows]
            }
        except Exception as exc:
            logger.error(f'❌ 获取评论列表失败: {exc}')
            raise
    
    async def create_comment(self, prompt_id: int, user_id: int, content: str, parent_id: int = None) -> int:
        """创建评论"""
        try:
            # 插入评论
            fields = {
                'prompt_id': prompt_id,
                'user_id': user_id,
                'content': content,
                'parent_id': parent_id
            }
            comment_id = await self.db.table_insert('prompt_comments', fields)
            
            # 增加评论计数
            update_sql = 'UPDATE prompts SET comment_count = comment_count + 1 WHERE id = ?'
            await self.db.execute(update_sql, [prompt_id])
            
            # 更新热度分数
            await self.update_hot_score(prompt_id)
            
            logger.info(f'✅ 创建评论成功: comment_id={comment_id}, prompt_id={prompt_id}')
            return comment_id
        except Exception as exc:
            logger.error(f'❌ 创建评论失败: {exc}')
            raise
    
    async def update_comment(self, comment_id: int, user_id: int, content: str) -> bool:
        """更新评论"""
        try:
            # 检查权限
            check_sql = 'SELECT user_id FROM prompt_comments WHERE id = ? AND is_deleted = 0'
            comment = await self.db.get(check_sql, [comment_id])
            
            if not comment:
                raise ValueError('评论不存在')
            
            if comment['user_id'] != user_id:
                raise PermissionError('无权编辑此评论')
            
            # 更新评论
            update_sql = 'UPDATE prompt_comments SET content = ?, is_edited = 1 WHERE id = ?'
            await self.db.execute(update_sql, [content, comment_id])
            
            logger.info(f'✅ 更新评论成功: comment_id={comment_id}')
            return True
        except Exception as exc:
            logger.error(f'❌ 更新评论失败: {exc}')
            raise
    
    async def delete_comment(self, comment_id: int, user_id: int, is_admin: bool = False) -> bool:
        """软删除评论（评论作者/提示词作者/管理员可删除）+ 级联删除所有子回复"""
        try:
            # 检查权限
            check_sql = """
                SELECT c.user_id, c.prompt_id, p.user_id as prompt_owner_id
                FROM prompt_comments c
                LEFT JOIN prompts p ON c.prompt_id = p.id
                WHERE c.id = ? AND c.is_deleted = 0
            """
            comment = await self.db.get(check_sql, [comment_id])
            
            if not comment:
                raise ValueError('评论不存在')
            
            # 权限检查：评论作者、提示词作者、管理员可删除
            if comment['user_id'] != user_id and comment['prompt_owner_id'] != user_id and not is_admin:
                raise PermissionError('无权删除此评论')
            
            # 递归软删除：标记该评论及其所有子回复为已删除
            # 使用递归CTE查找所有子孙评论
            delete_sql = """
                WITH RECURSIVE comment_tree AS (
                    -- 基础：选中要删除的评论
                    SELECT id FROM prompt_comments WHERE id = ?
                    UNION ALL
                    -- 递归：查找所有子评论
                    SELECT c.id FROM prompt_comments c
                    INNER JOIN comment_tree ct ON c.parent_id = ct.id
                    WHERE c.is_deleted = 0
                )
                UPDATE prompt_comments SET is_deleted = 1 WHERE id IN (SELECT id FROM comment_tree)
            """
            await self.db.execute(delete_sql, [comment_id])
            
            # 统计删除的评论数量（包括子回复）
            count_sql = """
                WITH RECURSIVE comment_tree AS (
                    SELECT id FROM prompt_comments WHERE id = ?
                    UNION ALL
                    SELECT c.id FROM prompt_comments c
                    INNER JOIN comment_tree ct ON c.parent_id = ct.id
                )
                SELECT COUNT(*) as deleted_count FROM comment_tree
            """
            count_result = await self.db.get(count_sql, [comment_id])
            deleted_count = count_result['deleted_count'] if count_result else 1
            
            # 减少评论计数（删除多少条就减多少）
            update_sql = f'''
                UPDATE prompts 
                SET comment_count = CASE 
                    WHEN comment_count >= {deleted_count} THEN comment_count - {deleted_count}
                    ELSE 0 
                END 
                WHERE id = ?
            '''
            await self.db.execute(update_sql, [comment['prompt_id']])
            
            # 更新热度分数
            await self.update_hot_score(comment['prompt_id'])
            
            logger.info(f'✅ 删除评论成功: comment_id={comment_id}, 级联删除 {deleted_count} 条')
            return True
        except Exception as exc:
            logger.error(f'❌ 删除评论失败: {exc}')
            raise
    
    async def get_author_other_prompts(self, user_id: int, exclude_prompt_id: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        """获取作者的其他公开提示词"""
        try:
            params = [user_id]
            where_sql = 'user_id = ? AND is_public = 1'
            
            if exclude_prompt_id:
                where_sql += ' AND id != ?'
                params.append(exclude_prompt_id)
            
            sql = f"""
                SELECT id, title, description, prompt_type, like_count, comment_count, view_count
                FROM prompts
                WHERE {where_sql}
                ORDER BY hot_score DESC, create_time DESC
                LIMIT ?
            """
            params.append(limit)
            
            rows = await self.db.query(sql, params)
            return [self._serialize_row(row) for row in rows]
        except Exception as exc:
            logger.error(f'❌ 获取作者其他提示词失败: {exc}')
            raise
    
    async def get_related_playground_shares(self, prompt_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """获取使用该提示词的公开操练场快照"""
        try:
            sql = """
                SELECT 
                    ps.share_code, ps.title, ps.view_count, ps.create_time,
                    ps.access_mode, ps.is_permanent, ps.expires_at,
                    u.name as creator_name, u.avatar as creator_avatar
                FROM playground_shares ps
                LEFT JOIN users u ON ps.user_id = u.id
                WHERE ps.prompt_id = ? 
                  AND ps.is_active = 1 
                  AND ps.access_mode = 'public'
                  AND (ps.is_permanent = 1 OR ps.expires_at > CURRENT_TIMESTAMP)
                ORDER BY ps.create_time DESC
                LIMIT ?
            """
            rows = await self.db.query(sql, [prompt_id, limit])
            shares = [self._serialize_row(row) for row in rows]

            remaining = max(0, limit - len(shares))
            if remaining > 0:
                legacy_sql = """
                    SELECT 
                        s.share_code,
                        p.title AS prompt_title,
                        s.view_count,
                        s.create_time,
                        s.expire_time,
                        u.name AS creator_name,
                        u.avatar AS creator_avatar
                    FROM prompt_shares s
                    LEFT JOIN prompts p ON s.prompt_id = p.id
                    LEFT JOIN users u ON p.user_id = u.id
                    WHERE s.prompt_id = ?
                    ORDER BY s.create_time DESC
                    LIMIT ?
                """
                legacy_rows = await self.db.query(legacy_sql, [prompt_id, remaining])
                for row in legacy_rows:
                    serialized = self._serialize_row(row)
                    share_code = serialized.get('share_code')
                    legacy_title = serialized.get('prompt_title') or (share_code and f"分享 {share_code}") or '历史分享'
                    shares.append({
                        'share_code': serialized.get('share_code'),
                        'title': legacy_title,
                        'view_count': serialized.get('view_count', 0),
                        'create_time': serialized.get('create_time'),
                        'creator_name': serialized.get('creator_name'),
                        'creator_avatar': serialized.get('creator_avatar'),
                        'access_mode': 'public',
                        'is_permanent': serialized.get('expire_time') is None,
                        'expires_at': serialized.get('expire_time'),
                        'has_password': False
                    })
            return shares
        except Exception as exc:
            logger.error(f'❌ 获取相关操练场快照失败: {exc}')
            raise

    async def record_visit(self, prompt_id: int, user_id: int):
        """记录访问足迹"""
        try:
            existing = await self.db.get(
                "SELECT id FROM prompt_visits WHERE prompt_id = ? AND user_id = ?",
                [prompt_id, user_id]
            )
            if existing:
                await self.db.execute(
                    "UPDATE prompt_visits SET visit_time = CURRENT_TIMESTAMP WHERE id = ?",
                    [existing['id']]
                )
            else:
                try:
                    await self.db.execute(
                        "INSERT INTO prompt_visits (prompt_id, user_id, visit_time) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        [prompt_id, user_id]
                    )
                except Exception:
                    # 处理并发情况下的唯一约束冲突
                    await self.db.execute(
                        "UPDATE prompt_visits SET visit_time = CURRENT_TIMESTAMP WHERE prompt_id = ? AND user_id = ?",
                        [prompt_id, user_id]
                    )
        except Exception as exc:
            logger.error(f'❌ 记录访问足迹失败: {exc}')
    
    async def get_recent_visitors(self, prompt_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近访问者"""
        try:
            sql = """
                SELECT 
                    v.user_id, v.visit_time,
                    u.name as user_name, u.avatar as user_avatar
                FROM prompt_visits v
                LEFT JOIN users u ON v.user_id = u.id
                WHERE v.prompt_id = ?
                ORDER BY v.visit_time DESC
                LIMIT ?
            """
            rows = await self.db.query(sql, [prompt_id, limit])
            return [self._serialize_row(row) for row in rows]
        except Exception as exc:
            logger.error(f'❌ 获取访问者列表失败: {exc}')
            raise

    @staticmethod
    def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """将数据库记录转换为JSON-friendly字典"""
        serialized: Dict[str, Any] = {}
        data = dict(row)
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat(sep=' ', timespec='seconds')
            else:
                serialized[key] = value
        return serialized
