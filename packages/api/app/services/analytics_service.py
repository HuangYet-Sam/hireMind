"""
Analytics Service.

Recruitment analytics, dashboard metrics, and reporting logic.
Uses Python-side calculations for SQLite compatibility.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.department import Department
from app.models.interview import Interview
from app.models.offer import Offer
from app.models.position import Position


class AnalyticsService:
    """Aggregates recruitment data for dashboards and reports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self, tenant_id: str, department_id: UUID | None = None) -> dict:
        """
        Return aggregate dashboard data.

        Includes:
        - open_positions: count of active positions
        - candidates_in_pipeline: count by stage
        - interviews_this_week: count
        - offers_pending: count awaiting approval
        - avg_time_to_hire: in days
        """
        # Open positions (status in ['open', 'draft'])
        pos_query = select(func.count()).select_from(Position).where(
            Position.tenant_id == tenant_id,
            Position.status.in_(["open", "draft"]),
        )
        if department_id is not None:
            pos_query = pos_query.where(Position.department_id == department_id)
        open_positions = (await self.db.execute(pos_query)).scalar_one()

        # Candidates in pipeline (status='active', stage not in ['hired', 'rejected'])
        cand_query = select(func.count()).select_from(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.status == "active",
            Candidate.stage.notin_(["hired", "rejected"]),
        )
        candidates_in_pipeline = (await self.db.execute(cand_query)).scalar_one()

        # Interviews with status='scheduled'
        int_query = select(func.count()).select_from(Interview).where(
            Interview.tenant_id == tenant_id,
            Interview.status == "scheduled",
        )
        interviews_scheduled = (await self.db.execute(int_query)).scalar_one()

        # Offers with status in ['draft', 'pending_approval']
        off_query = select(func.count()).select_from(Offer).where(
            Offer.tenant_id == tenant_id,
            Offer.status.in_(["draft", "pending_approval"]),
        )
        offers_pending = (await self.db.execute(off_query)).scalar_one()

        # Average time-to-hire: avg days between applied_at and updated_at for hired candidates
        hired_query = select(Candidate.applied_at, Candidate.updated_at).where(
            Candidate.tenant_id == tenant_id,
            Candidate.stage == "hired",
            Candidate.applied_at.isnot(None),
        )
        hired_rows = (await self.db.execute(hired_query)).all()

        if hired_rows:
            total_days = sum(
                (row.updated_at - row.applied_at).days
                for row in hired_rows
                if row.applied_at and row.updated_at
            )
            valid_count = sum(
                1 for row in hired_rows
                if row.applied_at and row.updated_at
            )
            avg_time_to_hire = round(total_days / valid_count, 1) if valid_count else 0.0
        else:
            avg_time_to_hire = 0.0

        return {
            "open_positions": open_positions,
            "candidates_in_pipeline": candidates_in_pipeline,
            "interviews_this_week": interviews_scheduled,
            "offers_pending": offers_pending,
            "avg_time_to_hire": avg_time_to_hire,
        }

    async def get_pipeline_funnel(
        self,
        tenant_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Return the hiring pipeline funnel data.

        Stages: applied -> screened -> interviewed -> offered -> hired -> rejected
        """
        # Use a single grouped query for efficiency
        query = (
            select(Candidate.stage, func.count().label("count"))
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
            )
            .group_by(Candidate.stage)
        )

        if date_from is not None:
            query = query.where(Candidate.applied_at >= date_from)
        if date_to is not None:
            query = query.where(Candidate.applied_at < date_to)

        rows = (await self.db.execute(query)).all()
        stage_counts = {row.stage: row.count for row in rows}

        # Return in defined order with zero-fill for missing stages
        ordered_stages = ["applied", "screened", "interviewed", "offered", "hired", "rejected"]
        stages = [
            {"stage": stage, "count": stage_counts.get(stage, 0)}
            for stage in ordered_stages
        ]

        return {"stages": stages}

    async def get_time_to_hire(
        self,
        tenant_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        group_by: str = "month",
    ) -> list[dict]:
        """Return average time-to-hire metrics grouped by period."""
        query = select(Candidate.applied_at, Candidate.updated_at).where(
            Candidate.tenant_id == tenant_id,
            Candidate.stage == "hired",
            Candidate.applied_at.isnot(None),
        )

        if date_from is not None:
            query = query.where(Candidate.applied_at >= date_from)
        if date_to is not None:
            query = query.where(Candidate.applied_at < date_to)

        rows = (await self.db.execute(query)).all()

        if not rows:
            return []

        # Group by period in Python for SQLite compatibility
        period_buckets: dict[str, list[int]] = {}

        for row in rows:
            if not row.applied_at or not row.updated_at:
                continue
            days = (row.updated_at - row.applied_at).days

            if group_by == "week":
                # ISO week: "2026-W03"
                iso_year, iso_week, _ = row.applied_at.isocalendar()
                period_key = f"{iso_year}-W{iso_week:02d}"
            elif group_by == "day":
                period_key = row.applied_at.strftime("%Y-%m-%d")
            else:
                # Default: month
                period_key = row.applied_at.strftime("%Y-%m")

            period_buckets.setdefault(period_key, []).append(days)

        result = []
        for period_key in sorted(period_buckets.keys()):
            values = period_buckets[period_key]
            avg_days = round(sum(values) / len(values), 1)
            result.append({
                "period": period_key,
                "avg_days": avg_days,
                "count": len(values),
            })

        return result

    async def get_source_effectiveness(self, tenant_id: str) -> list[dict]:
        """
        Return candidate source effectiveness.

        Columns: source, total, hired, conversion_rate
        """
        query = (
            select(
                Candidate.source,
                func.count().label("total"),
                func.count(
                    case((Candidate.stage == "hired", Candidate.id))
                ).label("hired"),
            )
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
            )
            .group_by(Candidate.source)
        )

        rows = (await self.db.execute(query)).all()

        result = []
        for row in rows:
            source_label = row.source or "unknown"
            total = row.total
            hired_count = row.hired
            conversion_rate = round(hired_count / total * 100, 1) if total > 0 else 0.0
            result.append({
                "source": source_label,
                "total": total,
                "hired": hired_count,
                "conversion_rate": conversion_rate,
            })

        # Sort by total descending
        result.sort(key=lambda x: x["total"], reverse=True)
        return result

    async def get_department_summary(self, tenant_id: str) -> list[dict]:
        """Return per-department recruitment metrics."""
        # Fetch active departments for the tenant
        dept_query = select(Department).where(
            Department.tenant_id == tenant_id,
            Department.status == "active",
        )
        departments = (await self.db.execute(dept_query)).scalars().all()

        result = []
        for dept in departments:
            # Count positions for this department
            pos_count_query = select(func.count()).select_from(Position).where(
                Position.department_id == dept.id,
            )
            pos_count = (await self.db.execute(pos_count_query)).scalar_one()

            # Count active candidates linked to those positions
            cand_count_query = (
                select(func.count())
                .select_from(Candidate)
                .join(Position, Candidate.position_id == Position.id)
                .where(
                    Position.department_id == dept.id,
                    Candidate.status == "active",
                )
            )
            cand_count = (await self.db.execute(cand_count_query)).scalar_one()

            result.append({
                "department": dept.name,
                "positions": pos_count,
                "candidates": cand_count,
            })

        # Sort by candidates descending
        result.sort(key=lambda x: x["candidates"], reverse=True)
        return result
