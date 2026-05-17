"""
HireMind Production Seed Data Script.

Populates the database with realistic sample data for:
  - Departments (6)
  - Positions (12)
  - Candidates (30)
  - Resumes (20)
  - Interviews (15)
  - Offers (8)
  - AI Tasks (10)

Idempotent: skips insertion if data already exists.
Usage:
    cd packages/api && python -m scripts.seed_data
    docker exec hiremind-api python -m scripts.seed_data
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: ensure app module path is resolvable when run directly
# ---------------------------------------------------------------------------
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func as sa_func, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import *  # noqa: F401,F403  — register all models
from app.models.ai_task import AiTask, TaskStatus, TaskType
from app.models.candidate import Candidate
from app.models.department import Department
from app.models.interview import Interview
from app.models.offer import Offer
from app.models.position import Position
from app.models.resume import Resume

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TENANT_ID = "default"
SEED_MARKER = "seed"  # used in tags / source_detail to mark seeded data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256(val: str) -> str:
    return hashlib.sha256(val.encode()).hexdigest()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(n: int) -> datetime:
    return now_utc() - timedelta(days=n)


def days_from_now(n: int) -> datetime:
    return now_utc() + timedelta(days=n)


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

DEPARTMENTS: list[dict[str, Any]] = [
    {
        "name": "技术研发部",
        "code": "ENG",
        "description": "负责公司核心产品的技术研发和架构设计",
        "headcount_limit": 80,
        "manager_name": "赵鹏",
        "sort_order": 1,
        "tree_path": "eng",
    },
    {
        "name": "产品设计部",
        "code": "PD",
        "description": "负责产品规划、设计和用户体验优化",
        "headcount_limit": 30,
        "manager_name": "孙婷",
        "sort_order": 2,
        "tree_path": "pd",
        "parent_code": "ENG",  # under tech
    },
    {
        "name": "市场营销部",
        "code": "MKT",
        "description": "负责品牌推广、市场活动和客户获取",
        "headcount_limit": 25,
        "manager_name": "周明",
        "sort_order": 3,
        "tree_path": "mkt",
    },
    {
        "name": "人力资源部",
        "code": "HR",
        "description": "负责人才招聘、员工发展和组织文化建设",
        "headcount_limit": 20,
        "manager_name": "吴丽",
        "sort_order": 4,
        "tree_path": "hr",
    },
    {
        "name": "财务部",
        "code": "FIN",
        "description": "负责公司财务管理、预算规划和风险控制",
        "headcount_limit": 15,
        "manager_name": "郑刚",
        "sort_order": 5,
        "tree_path": "fin",
    },
    {
        "name": "运营部",
        "code": "OPS",
        "description": "负责产品运营、数据运营和客户成功",
        "headcount_limit": 20,
        "manager_name": "冯涛",
        "sort_order": 6,
        "tree_path": "ops",
    },
]

POSITIONS: list[dict[str, Any]] = [
    # 8 open
    {
        "title": "高级前端工程师",
        "department_code": "ENG",
        "status": "open",
        "salary_min": 25000,
        "salary_max": 40000,
        "location": "北京",
        "description": "负责公司核心产品的前端架构设计和开发工作",
        "requirements": "5年以上前端开发经验，精通React/Vue，熟悉TypeScript，有大型项目架构经验",
        "required_skills": [{"name": "React"}, {"name": "Vue"}, {"name": "TypeScript"}, {"name": "Webpack"}, {"name": "Node.js"}],
        "required_exp_min": 5,
        "required_exp_max": 10,
        "priority": "high",
        "headcount": 2,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
    {
        "title": "后端工程师",
        "department_code": "ENG",
        "status": "open",
        "salary_min": 20000,
        "salary_max": 35000,
        "location": "北京",
        "description": "负责后端微服务的设计、开发和维护",
        "requirements": "3年以上Python/Java开发经验，熟悉微服务架构和数据库设计",
        "required_skills": [{"name": "Python"}, {"name": "FastAPI"}, {"name": "PostgreSQL"}, {"name": "Redis"}, {"name": "Docker"}],
        "required_exp_min": 3,
        "required_exp_max": 8,
        "priority": "high",
        "headcount": 3,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
    {
        "title": "AI算法工程师",
        "department_code": "ENG",
        "status": "open",
        "salary_min": 30000,
        "salary_max": 50000,
        "location": "北京",
        "description": "负责NLP和推荐系统算法的研发和优化",
        "requirements": "硕士及以上学历，熟悉深度学习框架，有NLP或推荐系统项目经验",
        "required_skills": [{"name": "PyTorch"}, {"name": "NLP"}, {"name": "Transformer"}, {"name": "Python"}, {"name": "ML"}],
        "required_exp_min": 3,
        "required_exp_max": 8,
        "priority": "high",
        "headcount": 2,
        "education_requirement": "硕士及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
    {
        "title": "产品经理",
        "department_code": "PD",
        "status": "open",
        "salary_min": 20000,
        "salary_max": 35000,
        "location": "北京",
        "description": "负责B端SaaS产品的规划和设计",
        "requirements": "3年以上B端产品经验，有HR SaaS产品经验优先",
        "required_skills": [{"name": "产品设计"}, {"name": "需求分析"}, {"name": "Axure"}, {"name": "SQL"}, {"name": "数据分析"}],
        "required_exp_min": 3,
        "required_exp_max": 8,
        "priority": "normal",
        "headcount": 1,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
    {
        "title": "UX设计师",
        "department_code": "PD",
        "status": "open",
        "salary_min": 18000,
        "salary_max": 30000,
        "location": "上海",
        "description": "负责产品的用户体验设计和交互优化",
        "requirements": "3年以上UX设计经验，精通Figma/Sketch，有设计系统搭建经验",
        "required_skills": [{"name": "Figma"}, {"name": "Sketch"}, {"name": "交互设计"}, {"name": "用户研究"}, {"name": "设计系统"}],
        "required_exp_min": 3,
        "required_exp_max": 7,
        "priority": "normal",
        "headcount": 1,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": True,
    },
    {
        "title": "DevOps工程师",
        "department_code": "ENG",
        "status": "open",
        "salary_min": 22000,
        "salary_max": 38000,
        "location": "北京",
        "description": "负责CI/CD流水线和云基础设施的运维",
        "requirements": "3年以上DevOps经验，精通Kubernetes和AWS/阿里云",
        "required_skills": [{"name": "Kubernetes"}, {"name": "Docker"}, {"name": "AWS"}, {"name": "Terraform"}, {"name": "CI/CD"}],
        "required_exp_min": 3,
        "required_exp_max": 8,
        "priority": "normal",
        "headcount": 1,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
    {
        "title": "项目经理",
        "department_code": "ENG",
        "status": "open",
        "salary_min": 20000,
        "salary_max": 35000,
        "location": "北京",
        "description": "负责技术项目的进度管理和跨部门协调",
        "requirements": "5年以上项目管理经验，PMP认证优先",
        "required_skills": [{"name": "项目管理"}, {"name": "Agile"}, {"name": "Scrum"}, {"name": "JIRA"}, {"name": "风险管理"}],
        "required_exp_min": 5,
        "required_exp_max": 10,
        "priority": "normal",
        "headcount": 1,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
    {
        "title": "数据分析师",
        "department_code": "OPS",
        "status": "open",
        "salary_min": 15000,
        "salary_max": 25000,
        "location": "上海",
        "description": "负责业务数据分析和可视化报表建设",
        "requirements": "2年以上数据分析经验，精通SQL和Python，有BI工具使用经验",
        "required_skills": [{"name": "SQL"}, {"name": "Python"}, {"name": "Tableau"}, {"name": "Excel"}, {"name": "统计学"}],
        "required_exp_min": 2,
        "required_exp_max": 5,
        "priority": "normal",
        "headcount": 2,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": True,
    },
    # 2 closed
    {
        "title": "市场专员",
        "department_code": "MKT",
        "status": "closed",
        "salary_min": 10000,
        "salary_max": 18000,
        "location": "北京",
        "description": "负责线上线下市场活动的策划和执行",
        "requirements": "2年以上市场推广经验，有SaaS行业经验优先",
        "required_skills": [{"name": "市场推广"}, {"name": "活动策划"}, {"name": "SEO"}, {"name": "SEM"}, {"name": "社媒运营"}],
        "required_exp_min": 2,
        "required_exp_max": 5,
        "priority": "normal",
        "headcount": 1,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
    {
        "title": "HRBP",
        "department_code": "HR",
        "status": "closed",
        "salary_min": 15000,
        "salary_max": 25000,
        "location": "北京",
        "description": "负责业务部门的人力资源合作伙伴工作",
        "requirements": "3年以上HRBP经验，了解业务，有组织发展经验",
        "required_skills": [{"name": "HRBP"}, {"name": "组织发展"}, {"name": "绩效管理"}, {"name": "人才发展"}, {"name": "劳动法"}],
        "required_exp_min": 3,
        "required_exp_max": 8,
        "priority": "normal",
        "headcount": 1,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
    # 2 filled
    {
        "title": "财务分析师",
        "department_code": "FIN",
        "status": "filled",
        "salary_min": 15000,
        "salary_max": 25000,
        "location": "北京",
        "description": "负责财务分析和预算管理工作",
        "requirements": "3年以上财务分析经验，CPA/CFA优先",
        "required_skills": [{"name": "财务分析"}, {"name": "Excel"}, {"name": "SAP"}, {"name": "预算管理"}, {"name": "风险管理"}],
        "required_exp_min": 3,
        "required_exp_max": 7,
        "priority": "normal",
        "headcount": 1,
        "filled_count": 1,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
    {
        "title": "运营经理",
        "department_code": "OPS",
        "status": "filled",
        "salary_min": 20000,
        "salary_max": 35000,
        "location": "上海",
        "description": "负责产品运营策略制定和执行",
        "requirements": "5年以上互联网运营经验，有团队管理经验",
        "required_skills": [{"name": "运营策略"}, {"name": "数据分析"}, {"name": "用户增长"}, {"name": "团队管理"}, {"name": "项目协调"}],
        "required_exp_min": 5,
        "required_exp_max": 10,
        "priority": "high",
        "headcount": 1,
        "filled_count": 1,
        "education_requirement": "本科及以上",
        "employment_type": "full_time",
        "is_remote": False,
    },
]

CANDIDATES: list[dict[str, Any]] = [
    # (name, email, phone, stage, source, position_title, experience, education, current_company, current_title)
    # --- applied / new (5) ---
    ("张伟", "zhangwei@example.com", "13800001001", "applied", "boss直聘", "高级前端工程师",
     6, "本科", "字节跳动", "前端工程师"),
    ("李娜", "lina@example.com", "13800001002", "applied", "猎聘", "后端工程师",
     4, "硕士", "阿里巴巴", "后端开发工程师"),
    ("王磊", "wanglei@example.com", "13800001003", "applied", "拉勾", "AI算法工程师",
     3, "硕士", "百度", "算法工程师"),
    ("刘洋", "liuyang@example.com", "13800001004", "applied", "内推", "产品经理",
     5, "本科", "腾讯", "高级产品经理"),
    ("陈静", "chenjing@example.com", "13800001005", "applied", "官网", "UX设计师",
     4, "本科", "网易", "UX设计师"),

    # --- screened (5) ---
    ("赵敏", "zhaomin@example.com", "13800001006", "screened", "boss直聘", "后端工程师",
     6, "硕士", "华为", "高级后端工程师"),
    ("孙浩", "sunhao@example.com", "13800001007", "screened", "猎聘", "AI算法工程师",
     5, "博士", "商汤科技", "高级算法工程师"),
    ("周婷", "zhouting@example.com", "13800001008", "screened", "内推", "数据分析师",
     3, "本科", "美团", "数据分析师"),
    ("吴强", "wuqiang@example.com", "13800001009", "screened", "拉勾", "DevOps工程师",
     4, "本科", "京东", "DevOps工程师"),
    ("郑丽", "zhengli@example.com", "13800001010", "screened", "官网", "产品经理",
     4, "本科", "小米", "产品经理"),

    # --- interviewed (8) ---
    ("黄勇", "huangyong@example.com", "13800001011", "interviewed", "boss直聘", "高级前端工程师",
     7, "硕士", "快手", "前端技术负责人"),
    ("林芳", "linfang@example.com", "13800001012", "interviewed", "猎聘", "后端工程师",
     5, "本科", "滴滴", "高级后端工程师"),
    ("何军", "hejun@example.com", "13800001013", "interviewed", "内推", "AI算法工程师",
     4, "硕士", "旷视科技", "AI工程师"),
    ("罗晓", "luoxiao@example.com", "13800001014", "interviewed", "拉勾", "项目经理",
     8, "本科", "联想", "高级项目经理"),
    ("梁敏", "liangmin@example.com", "13800001015", "interviewed", "boss直聘", "数据分析师",
     3, "硕士", "携程", "数据分析师"),
    ("宋杰", "songjie@example.com", "13800001016", "interviewed", "猎聘", "DevOps工程师",
     5, "本科", "蚂蚁集团", "SRE工程师"),
    ("谢琳", "xielin@example.com", "13800001017", "interviewed", "官网", "UX设计师",
     5, "硕士", "OPPO", "高级UX设计师"),
    ("韩磊", "hanlei@example.com", "13800001018", "interviewed", "内推", "产品经理",
     6, "本科", "拼多多", "高级产品经理"),

    # --- offered (4) ---
    ("唐亮", "tangliang@example.com", "13800001019", "offered", "boss直聘", "高级前端工程师",
     8, "硕士", "腾讯", "前端架构师"),
    ("许萍", "xuping@example.com", "13800001020", "offered", "猎聘", "AI算法工程师",
     6, "博士", "微软亚洲研究院", "研究员"),
    ("邓超", "dengchao@example.com", "13800001021", "offered", "内推", "DevOps工程师",
     7, "本科", "谷歌中国", "SRE高级工程师"),
    ("冯雪", "fengxue@example.com", "13800001022", "offered", "拉勾", "数据分析师",
     4, "硕士", "字节跳动", "高级数据分析师"),

    # --- hired (4) ---
    ("曹军", "caojun@example.com", "13800001023", "hired", "boss直聘", "财务分析师",
     5, "硕士", "德勤", "高级审计师"),
    ("袁芳", "yuanfang@example.com", "13800001024", "hired", "猎聘", "运营经理",
     7, "本科", "阿里巴巴", "运营总监"),
    ("蒋鹏", "jiangpeng@example.com", "13800001025", "hired", "内推", "后端工程师",
     5, "硕士", "华为", "高级工程师"),
    ("沈慧", "shenhui@example.com", "13800001026", "hired", "官网", "产品经理",
     6, "本科", "腾讯", "产品专家"),

    # --- rejected (4) ---
    ("彭阳", "pengyang@example.com", "13800001027", "rejected", "boss直聘", "高级前端工程师",
     2, "本科", "外包公司A", "前端开发"),
    ("潘婷", "panting@example.com", "13800001028", "rejected", "拉勾", "市场专员",
     1, "本科", "应届毕业生", "无"),
    ("丁伟", "dingwei@example.com", "13800001029", "rejected", "猎聘", "AI算法工程师",
     2, "本科", "创业公司B", "算法实习生"),
    ("于静", "yujing@example.com", "13800001030", "rejected", "官网", "HRBP",
     3, "本科", "中小企业C", "人事专员"),
]


def _build_candidate_profile(
    name: str, experience: int, education: str, current_company: str, current_title: str
) -> dict:
    return {
        "basic_info": {
            "name": name,
            "years_of_experience": experience,
            "education": education,
            "current_company": current_company,
            "current_title": current_title,
            "location": "北京" if experience > 3 else "上海",
        },
        "skills": [],
        "preferences": {
            "expected_salary": None,
        },
    }


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------

async def seed_departments(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Create 6 departments, return {code: id} mapping."""
    print("🏢  Seeding departments ...")

    # Check existing
    existing = await session.execute(
        select(Department).where(Department.tenant_id == TENANT_ID)
    )
    existing_depts = {d.code: d for d in existing.scalars().all()}
    if len(existing_depts) >= 6:
        print(f"   ↳ Skip: {len(existing_depts)} departments already exist")
        return {code: d.id for code, d in existing_depts.items()}

    code_to_id: dict[str, uuid.UUID] = {}
    created: list[tuple[Department, str | None]] = []  # (dept, parent_code)

    for dept_data in DEPARTMENTS:
        code = dept_data["code"]
        if code in existing_depts:
            code_to_id[code] = existing_depts[code].id
            continue

        parent_code = dept_data.get("parent_code")
        # Copy data without parent_code for Department constructor
        ctor_data = {k: v for k, v in dept_data.items() if k != "parent_code"}
        dept = Department(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            status="active",
            **ctor_data,
        )
        session.add(dept)
        created.append((dept, parent_code))
        code_to_id[code] = dept.id

    await session.flush()

    # Set parent_id for departments that have parent_code
    for dept, parent_code in created:
        if parent_code and parent_code in code_to_id:
            dept.parent_id = code_to_id[parent_code]

    await session.flush()
    print(f"   ↳ Created {len(created)} departments (total: {len(code_to_id)})")
    return code_to_id


async def seed_positions(
    session: AsyncSession, dept_map: dict[str, uuid.UUID]
) -> dict[str, uuid.UUID]:
    """Create 12 positions, return {title: id} mapping."""
    print("📋  Seeding positions ...")

    existing = await session.execute(
        select(Position).where(Position.tenant_id == TENANT_ID)
    )
    existing_positions = {p.title: p for p in existing.scalars().all()}
    if len(existing_positions) >= 12:
        print(f"   ↳ Skip: {len(existing_positions)} positions already exist")
        return {t: p.id for t, p in existing_positions.items()}

    title_to_id: dict[str, uuid.UUID] = {}
    count = 0

    for pos_data in POSITIONS:
        title = pos_data["title"]
        if title in existing_positions:
            title_to_id[title] = existing_positions[title].id
            continue

        dept_code = pos_data.pop("department_code")
        department_id = dept_map[dept_code]

        pos = Position(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            department_id=department_id,
            published_at=now_utc() if pos_data["status"] == "open" else None,
            closed_at=now_utc() if pos_data["status"] == "closed" else None,
            jd_text=pos_data.get("description"),
            benefits="五险一金、带薪年假、弹性工作、员工股票期权、定期团建",
            **pos_data,
        )
        session.add(pos)
        title_to_id[title] = pos.id
        count += 1

    await session.flush()
    print(f"   ↳ Created {count} positions (total: {len(title_to_id)})")
    return title_to_id


async def seed_candidates(
    session: AsyncSession, pos_map: dict[str, uuid.UUID]
) -> list[uuid.UUID]:
    """Create 30 candidates, return list of IDs."""
    print("👤  Seeding candidates ...")

    # Quick existence check by counting
    count_q = await session.scalar(
        select(sa_func.count()).select_from(Candidate).where(
            Candidate.tenant_id == TENANT_ID
        )
    )
    if count_q and count_q >= 30:
        print(f"   ↳ Skip: {count_q} candidates already exist")
        result = await session.execute(
            select(Candidate.id).where(Candidate.tenant_id == TENANT_ID).limit(30)
        )
        return [row[0] for row in result.all()]

    candidate_ids: list[uuid.UUID] = []
    count = 0

    for (
        name, email, phone, stage, source, position_title,
        exp, edu, company, title,
    ) in CANDIDATES:
        # Check by email_hash
        email_hash = sha256(email)
        phone_hash = sha256(phone)
        existing = await session.scalar(
            select(Candidate).where(Candidate.email_hash == email_hash)
        )
        if existing:
            candidate_ids.append(existing.id)
            continue

        position_id = pos_map.get(position_title)
        profile = _build_candidate_profile(name, exp, edu, company, title)

        c = Candidate(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            email=email,
            phone=phone,
            name_encrypted=name,
            email_hash=email_hash,
            phone_hash=phone_hash,
            name_hash=sha256(name),
            stage=stage,
            status="active" if stage != "rejected" else "inactive",
            source=source,
            source_detail=SEED_MARKER,
            position_id=position_id,
            profile=profile,
            credibility_score=round(70 + hash(name) % 25, 1),
            credibility_grade="A" if hash(name) % 3 != 0 else "B",
            tags=[SEED_MARKER],
            applied_at=days_ago(abs(hash(name)) % 30 + 1),
            last_activity_at=days_ago(abs(hash(email)) % 7),
            summary=f"{name}，{exp}年{title}经验，来自{company}",
        )
        session.add(c)
        candidate_ids.append(c.id)
        count += 1

    await session.flush()
    print(f"   ↳ Created {count} candidates (total collected: {len(candidate_ids)})")
    return candidate_ids


async def seed_resumes(session: AsyncSession, candidate_ids: list[uuid.UUID]) -> None:
    """Create 20 resumes for the first 20 candidates."""
    print("📄  Seeding resumes ...")

    count_q = await session.scalar(
        select(sa_func.count()).select_from(Resume)
    )
    if count_q and count_q >= 20:
        print(f"   ↳ Skip: {count_q} resumes already exist")
        return

    statuses = ["completed"] * 10 + ["pending"] * 4 + ["failed"] * 3 + ["processing"] * 3
    skills_pool = [
        ["JavaScript", "TypeScript", "React", "Vue", "HTML5", "CSS3"],
        ["Python", "FastAPI", "Django", "PostgreSQL", "Redis"],
        ["PyTorch", "TensorFlow", "NLP", "深度学习", "计算机视觉"],
        ["SQL", "Python", "Tableau", "PowerBI", "Excel"],
        ["Docker", "Kubernetes", "AWS", "Jenkins", "Terraform"],
        ["产品设计", "Figma", "Axure", "用户研究", "交互设计"],
        ["项目管理", "Agile", "Scrum", "JIRA", "Confluence"],
        ["市场推广", "SEO", "SEM", "内容运营", "社交媒体"],
        ["HR管理", "招聘", "绩效管理", "组织发展", "劳动法"],
        ["财务分析", "Excel", "SAP", "预算管理", "审计"],
    ]

    count = 0
    for i, cand_id in enumerate(candidate_ids[:20]):
        existing = await session.scalar(
            select(Resume).where(Resume.candidate_id == cand_id).limit(1)
        )
        if existing:
            continue

        parse_status = statuses[i % len(statuses)]
        skills = skills_pool[i % len(skills_pool)]
        file_type = "pdf" if i % 3 != 0 else "docx"
        file_name = f"resume_{cand_id.hex[:8]}.{file_type}"

        parsed = None
        if parse_status == "completed":
            parsed = {
                "skills": skills,
                "work_experience": [
                    {"company": "公司A", "role": "工程师", "duration": "2020-2023"}
                ],
                "education": [{"school": "北京大学", "degree": "本科", "major": "计算机科学"}],
                "summary": f"候选人 #{i+1} 的简历解析结果",
            }

        r = Resume(
            id=uuid.uuid4(),
            candidate_id=cand_id,
            original_filename=file_name,
            file_path=f"/uploads/resumes/{file_name}",
            file_type=file_type,
            file_size=50000 + i * 10000,
            content_type="application/pdf" if file_type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            source="upload",
            parse_status=parse_status,
            parsed_data=parsed,
            tenant_id=TENANT_ID,
            file_hash=sha256(f"resume_{i}"),
            page_count=2 + (i % 4),
        )
        session.add(r)
        count += 1

    await session.flush()
    print(f"   ↳ Created {count} resumes")


async def seed_interviews(
    session: AsyncSession,
    candidate_ids: list[uuid.UUID],
    pos_map: dict[str, uuid.UUID],
) -> None:
    """Create 15 interviews."""
    print("🗓️   Seeding interviews ...")

    count_q = await session.scalar(
        select(sa_func.count()).select_from(Interview)
    )
    if count_q and count_q >= 15:
        print(f"   ↳ Skip: {count_q} interviews already exist")
        return

    interview_types = ["technical", "cultural", "phone_screen", "behavioral", "final"]
    statuses_dist = ["scheduled"] * 5 + ["completed"] * 7 + ["cancelled"] * 3
    recommendations = ["strong_yes", "yes", "no", "strong_no"]

    # Pick 15 candidates from the pool (prefer those in interview+ stages)
    interview_candidates = candidate_ids[10:25]  # middle section likely interviewed
    positions_list = list(pos_map.values())

    count = 0
    for i, cand_id in enumerate(interview_candidates[:15]):
        existing = await session.scalar(
            select(Interview).where(Interview.candidate_id == cand_id).limit(1)
        )
        if existing:
            continue

        status = statuses_dist[i % len(statuses_dist)]
        int_type = interview_types[i % len(interview_types)]
        pos_id = positions_list[i % len(positions_list)]

        # Time distribution: half past, half future
        if i < 8:
            scheduled = days_ago((i + 1) * 2)
        else:
            scheduled = days_from_now((i - 7))

        feedback = None
        score = None
        completed_at = None
        cancelled_at = None

        if status == "completed":
            score = round(5.0 + (i % 5), 1)
            feedback = f"面试表现{'优秀' if score >= 8 else '良好' if score >= 7 else '一般'}，{'推荐进入下一轮' if score >= 7 else '建议进一步评估'}"
            completed_at = scheduled + timedelta(hours=1)
        elif status == "cancelled":
            cancelled_at = scheduled + timedelta(hours=2)
            feedback = "候选人因个人原因取消面试"

        interview = Interview(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            candidate_id=cand_id,
            position_id=pos_id,
            round_number=1 + (i % 3),
            interview_type=int_type,
            status=status,
            scheduled_at=scheduled,
            duration_minutes=[30, 45, 60, 90][i % 4],
            location="北京总部 3F-会议室" if i % 2 == 0 else "腾讯会议 ID:888-000-" + str(1000 + i),
            overall_score=score,
            recommendation=recommendations[i % len(recommendations)] if status == "completed" else None,
            summary=feedback,
            completed_at=completed_at,
            cancelled_at=cancelled_at,
            cancel_reason="候选人取消" if status == "cancelled" else None,
        )
        session.add(interview)
        count += 1

    await session.flush()
    print(f"   ↳ Created {count} interviews")


async def seed_offers(
    session: AsyncSession,
    candidate_ids: list[uuid.UUID],
    pos_map: dict[str, uuid.UUID],
) -> None:
    """Create 8 offers."""
    print("💰  Seeding offers ...")

    count_q = await session.scalar(
        select(sa_func.count()).select_from(Offer)
    )
    if count_q and count_q >= 8:
        print(f"   ↳ Skip: {count_q} offers already exist")
        return

    # 4 offered-stage + 4 hired-stage candidates
    offer_candidates = candidate_ids[18:26]  # offered + hired
    positions_list = list(pos_map.values())

    offer_configs = [
        {"status": "sent", "base_salary": 35000, "sign_on_bonus": 30000},
        {"status": "sent", "base_salary": 40000, "sign_on_bonus": 50000},
        {"status": "pending_approval", "base_salary": 30000, "sign_on_bonus": 0},
        {"status": "pending_approval", "base_salary": 28000, "sign_on_bonus": 0},
        {"status": "accepted", "base_salary": 20000, "sign_on_bonus": 10000},
        {"status": "accepted", "base_salary": 32000, "sign_on_bonus": 20000},
        {"status": "rejected", "base_salary": 18000, "sign_on_bonus": 0},
        {"status": "withdrawn", "base_salary": 25000, "sign_on_bonus": 0},
    ]

    count = 0
    for i, cand_id in enumerate(offer_candidates[:8]):
        existing = await session.scalar(
            select(Offer).where(Offer.candidate_id == cand_id).limit(1)
        )
        if existing:
            continue

        cfg = offer_configs[i]
        pos_id = positions_list[i % len(positions_list)]

        sent_at = days_ago(10 - i) if cfg["status"] in ("sent", "accepted", "rejected") else None
        responded_at = days_ago(7 - i) if cfg["status"] in ("accepted", "rejected") else None

        o = Offer(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            candidate_id=cand_id,
            position_id=pos_id,
            status=cfg["status"],
            base_salary=cfg["base_salary"],
            annual_bonus_months=2.0 + (i % 3),
            sign_on_bonus=cfg["sign_on_bonus"],
            equity="期权 10,000 股（4年归属）" if i < 4 else None,
            benefits_summary="五险一金全额缴纳、补充医疗保险、年度体检、弹性工作、带薪年假15天",
            proposed_start_date=days_from_now(14 + i * 3),
            probation_months=3,
            work_location="北京" if i % 2 == 0 else "上海",
            employment_type="full_time",
            notes=f"Offer #{i+1} — {cfg['status']}",
            sent_at=sent_at,
            responded_at=responded_at,
            response_note="薪资符合预期" if cfg["status"] == "accepted" else ("薪资低于预期" if cfg["status"] == "rejected" else None),
            expiry_date=days_from_now(7),
        )
        session.add(o)
        count += 1

    await session.flush()
    print(f"   ↳ Created {count} offers")


async def seed_ai_tasks(session: AsyncSession) -> None:
    """Create 10 AI tasks."""
    print("🤖  Seeding AI tasks ...")

    count_q = await session.scalar(
        select(sa_func.count()).select_from(AiTask)
    )
    if count_q and count_q >= 10:
        print(f"   ↳ Skip: {count_q} AI tasks already exist")
        return

    tasks_config: list[dict[str, Any]] = [
        {
            "task_type": TaskType.resume_parse,
            "status": TaskStatus.completed,
            "input_data": json.dumps({"resume_id": "sample-1", "file_path": "/uploads/resume_1.pdf"}),
            "output_data": json.dumps({"parsed_skills": ["Python", "FastAPI"], "confidence": 0.95}),
        },
        {
            "task_type": TaskType.resume_parse,
            "status": TaskStatus.completed,
            "input_data": json.dumps({"resume_id": "sample-2", "file_path": "/uploads/resume_2.docx"}),
            "output_data": json.dumps({"parsed_skills": ["React", "TypeScript"], "confidence": 0.88}),
        },
        {
            "task_type": TaskType.candidate_match,
            "status": TaskStatus.completed,
            "input_data": json.dumps({"position_id": "sample-pos-1", "candidate_ids": ["c1", "c2", "c3"]}),
            "output_data": json.dumps({"matches": [{"candidate_id": "c1", "score": 0.92}, {"candidate_id": "c2", "score": 0.85}]}),
        },
        {
            "task_type": TaskType.candidate_match,
            "status": TaskStatus.running,
            "input_data": json.dumps({"position_id": "sample-pos-2", "candidate_ids": ["c4", "c5"]}),
            "output_data": None,
        },
        {
            "task_type": TaskType.batch_score,
            "status": TaskStatus.completed,
            "input_data": json.dumps({"position_id": "sample-pos-3", "batch_size": 50}),
            "output_data": json.dumps({"scored": 50, "avg_score": 0.73}),
        },
        {
            "task_type": TaskType.batch_score,
            "status": TaskStatus.pending,
            "input_data": json.dumps({"position_id": "sample-pos-4", "batch_size": 100}),
            "output_data": None,
        },
        {
            "task_type": TaskType.report_generate,
            "status": TaskStatus.completed,
            "input_data": json.dumps({"report_type": "monthly_summary", "month": "2026-04"}),
            "output_data": json.dumps({"file_url": "/reports/monthly_2026_04.pdf"}),
        },
        {
            "task_type": TaskType.report_generate,
            "status": TaskStatus.failed,
            "input_data": json.dumps({"report_type": "weekly_summary", "week": "2026-W19"}),
            "output_data": None,
            "error_message": "数据源连接超时",
        },
        {
            "task_type": TaskType.data_import,
            "status": TaskStatus.completed,
            "input_data": json.dumps({"source": "boss直聘", "file_path": "/imports/boss_2026_05.csv", "count": 200}),
            "output_data": json.dumps({"imported": 198, "skipped": 2, "errors": 0}),
        },
        {
            "task_type": TaskType.data_import,
            "status": TaskStatus.failed,
            "input_data": json.dumps({"source": "猎聘", "file_path": "/imports/lp_2026_05.xlsx", "count": 150}),
            "output_data": None,
            "error_message": "文件格式不正确，无法解析",
        },
    ]

    count = 0
    for cfg in tasks_config:
        t = AiTask(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            task_type=cfg["task_type"],
            status=cfg["status"],
            input_data=cfg["input_data"],
            output_data=cfg.get("output_data"),
            error_message=cfg.get("error_message"),
            created_by="seed_script",
        )
        session.add(t)
        count += 1

    await session.flush()
    print(f"   ↳ Created {count} AI tasks")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("=" * 60)
    print("🌱  HireMind Seed Data Script")
    print("=" * 60)

    engine = create_async_engine(
        settings.async_database_url,
        pool_size=5,
        max_overflow=2,
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            dept_map = await seed_departments(session)
            pos_map = await seed_positions(session, dept_map)
            candidate_ids = await seed_candidates(session, pos_map)
            await seed_resumes(session, candidate_ids)
            await seed_interviews(session, candidate_ids, pos_map)
            await seed_offers(session, candidate_ids, pos_map)
            await seed_ai_tasks(session)

    await engine.dispose()

    print()
    print("=" * 60)
    print("✅  Seed data complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
