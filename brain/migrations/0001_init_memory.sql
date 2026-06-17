-- 迁移：初始化 AI 宠物记忆数据库
-- 说明：SQLite 不支持 MySQL 风格的 COMMENT 语法，所以这里同时使用 SQL 注释和 schema_comments 表保存中文注释。
-- 约束：不使用外键约束。

-- 表：memories，中文注释：长期记忆表，保存用户显式记忆和模型提炼出的长期有用信息。
create table if not exists memories (
    -- 字段：id，中文注释：记忆主键ID。
    id integer primary key autoincrement,
    -- 字段：key，中文注释：记忆键名，用于区分记忆类型或主题。
    key text not null,
    -- 字段：value，中文注释：记忆内容，保存可被后续对话召回的信息。
    value text not null,
    -- 字段：tags，中文注释：记忆标签JSON数组，用于筛选和分类。
    tags text not null default '[]',
    -- 字段：importance，中文注释：重要程度，范围1到5，数字越大越重要。
    importance integer not null default 3,
    -- 字段：created_at，中文注释：创建时间。
    created_at text not null default current_timestamp,
    -- 字段：updated_at，中文注释：更新时间。
    updated_at text not null default current_timestamp
);

-- 表：episodes，中文注释：对话片段表，保存每一轮用户输入和宠物回复。
create table if not exists episodes (
    -- 字段：id，中文注释：对话片段主键ID。
    id integer primary key autoincrement,
    -- 字段：device_id，中文注释：设备标识，用于区分不同硬件或模拟器来源。
    device_id text not null,
    -- 字段：user_text，中文注释：用户输入文本。
    user_text text not null,
    -- 字段：assistant_text，中文注释：宠物回复文本。
    assistant_text text not null,
    -- 字段：expression，中文注释：宠物表情枚举值。
    expression text not null,
    -- 字段：motion，中文注释：宠物动作枚举值。
    motion text not null,
    -- 字段：created_at，中文注释：创建时间。
    created_at text not null default current_timestamp
);

-- 表：schema_comments，中文注释：数据库中文注释表，用于在 SQLite 中持久化保存表名和字段名说明。
create table if not exists schema_comments (
    -- 字段：id，中文注释：注释记录主键ID。
    id integer primary key autoincrement,
    -- 字段：object_type，中文注释：注释对象类型，取值为table或column。
    object_type text not null,
    -- 字段：table_name，中文注释：表名。
    table_name text not null,
    -- 字段：column_name，中文注释：字段名；表注释时为空字符串。
    column_name text not null default '',
    -- 字段：comment，中文注释：中文注释内容。
    comment text not null,
    -- 字段：created_at，中文注释：创建时间。
    created_at text not null default current_timestamp,
    -- 字段：updated_at，中文注释：更新时间。
    updated_at text not null default current_timestamp
);

create unique index if not exists idx_schema_comments_object
on schema_comments (object_type, table_name, column_name);

create index if not exists idx_memories_importance_updated_at
on memories (importance, updated_at);

create index if not exists idx_episodes_created_at
on episodes (created_at);

insert into schema_comments (object_type, table_name, column_name, comment)
values
    ('table', 'memories', '', '长期记忆表，保存用户显式记忆和模型提炼出的长期有用信息。'),
    ('column', 'memories', 'id', '记忆主键ID。'),
    ('column', 'memories', 'key', '记忆键名，用于区分记忆类型或主题。'),
    ('column', 'memories', 'value', '记忆内容，保存可被后续对话召回的信息。'),
    ('column', 'memories', 'tags', '记忆标签JSON数组，用于筛选和分类。'),
    ('column', 'memories', 'importance', '重要程度，范围1到5，数字越大越重要。'),
    ('column', 'memories', 'created_at', '创建时间。'),
    ('column', 'memories', 'updated_at', '更新时间。'),
    ('table', 'episodes', '', '对话片段表，保存每一轮用户输入和宠物回复。'),
    ('column', 'episodes', 'id', '对话片段主键ID。'),
    ('column', 'episodes', 'device_id', '设备标识，用于区分不同硬件或模拟器来源。'),
    ('column', 'episodes', 'user_text', '用户输入文本。'),
    ('column', 'episodes', 'assistant_text', '宠物回复文本。'),
    ('column', 'episodes', 'expression', '宠物表情枚举值。'),
    ('column', 'episodes', 'motion', '宠物动作枚举值。'),
    ('column', 'episodes', 'created_at', '创建时间。'),
    ('table', 'schema_comments', '', '数据库中文注释表，用于在 SQLite 中持久化保存表名和字段名说明。'),
    ('column', 'schema_comments', 'id', '注释记录主键ID。'),
    ('column', 'schema_comments', 'object_type', '注释对象类型，取值为table或column。'),
    ('column', 'schema_comments', 'table_name', '表名。'),
    ('column', 'schema_comments', 'column_name', '字段名；表注释时为空字符串。'),
    ('column', 'schema_comments', 'comment', '中文注释内容。'),
    ('column', 'schema_comments', 'created_at', '创建时间。'),
    ('column', 'schema_comments', 'updated_at', '更新时间。')
on conflict(object_type, table_name, column_name) do update set
    comment = excluded.comment,
    updated_at = current_timestamp;
