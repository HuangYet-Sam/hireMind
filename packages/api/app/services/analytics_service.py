"""
Analytics Service.

Recruitment analytics, dashboard metrics, and reporting logic.
Uses Python-side calculations for SQLite compatibility.
"""

from datetime import date, datetime
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

    # ══════════════════════════════════════════════════════════════════
    # M8: Enhanced Analytics Methods
    # ══════════════════════════════════════════════════════════════════

    async def funnel_drilldown(
        self,
        stage: str,
        tenant_id: str,
        filters: dict | None = None,
    ) -> dict:
        """漏斗钻取 — 点击某阶段下探到具体候选人/岗位。

        Args:
            stage: Pipeline stage to drill into (applied/screened/interviewed/offered/hired/rejected).
            tenant_id: Tenant scope.
            filters: Optional filters (position_id, source, date_from, date_to).

        Returns:
            Dict with stage, items (drill-down detail), and optional sub_funnel.
        """
        filters = filters or {}

        # Build base query for candidates at the given stage
        query = select(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.stage == stage,
            Candidate.status == "active",
        )

        # Apply optional filters
        if filters.get("position_id"):
            query = query.where(Candidate.position_id == filters["position_id"])
        if filters.get("source"):
            query = query.where(Candidate.source == filters["source"])
        if filters.get("date_from"):
            query = query.where(Candidate.applied_at >= filters["date_from"])
        if filters.get("date_to"):
            query = query.where(Candidate.applied_at < filters["date_to"])

        query = query.order_by(Candidate.updated_at.desc()).limit(100)
        rows = (await self.db.execute(query)).scalars().all()

        items = []
        for c in rows:
            item = {
                "candidate_id": str(c.id),
                "name": c.name,
                "source": c.source,
                "applied_at": str(c.applied_at) if c.applied_at else None,
                "stage": c.stage,
                "position_id": str(c.position_id) if c.position_id else None,
                "summary": c.summary,
            }
            # Enrich with position title if available
            if c.position_id:
                pos = await self.db.scalar(
                    select(Position.title).where(Position.id == c.position_id)
                )
                item["position_title"] = pos
            items.append(item)

        # Build sub-funnel: distribution of these candidates' next stages
        sub_funnel = None
        if stage in ("applied", "screened", "interviewed", "offered"):
            sub_stages = {
                "applied": ["screened", "interviewed", "offered", "hired", "rejected"],
                "screened": ["interviewed", "offered", "hired", "rejected"],
                "interviewed": ["offered", "hired", "rejected"],
                "offered": ["hired", "rejected"],
            }
            next_stages = sub_stages.get(stage, [])
            if next_stages:
                position_ids = [c.position_id for c in rows if c.position_id]
                sub_query = (
                    select(Candidate.stage, func.count().label("count"))
                    .where(
                        Candidate.tenant_id == tenant_id,
                        Candidate.position_id.in_(position_ids) if position_ids else Candidate.tenant_id == tenant_id,
                        Candidate.status == "active",
                    )
                    .group_by(Candidate.stage)
                )
                sub_rows = (await self.db.execute(sub_query)).all()
                stage_counts = {r.stage: r.count for r in sub_rows}
                total = sum(stage_counts.get(s, 0) for s in next_stages) or 1
                from app.schemas.dashboard import FunnelStage as FS
                sub_funnel = [
                    FS(
                        stage=s,
                        label=s,
                        count=stage_counts.get(s, 0),
                        conversion_rate=round(stage_counts.get(s, 0) / total * 100, 1) if total else 0,
                        cumulative_rate=None,
                    )
                    for s in next_stages
                ]

        from app.schemas.dashboard import FunnelDrilldown
        result = FunnelDrilldown(
            stage=stage,
            items=items,
            sub_funnel=sub_funnel,
        )
        return result.model_dump()

    async def get_comparison(
        self,
        metric: str,
        period: str,
        tenant_id: str,
    ) -> dict:
        """同比环比分析。

        Args:
            metric: 指标名 (candidates/interviews/offers/hires/time_to_hire).
            period: 对比周期 (mom=环比, yoy=同比).
            tenant_id: Tenant scope.

        Returns:
            ComparisonData dict with current, previous, change, change_percent.
        """
        from datetime import timedelta, timezone
        now = datetime.now(timezone.utc)

        # Determine comparison periods
        if period == "yoy":
            # Year-over-year: this month vs same month last year
            current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_end = now
            prev_start = current_start.replace(year=current_start.year - 1)
            prev_end = current_end.replace(year=current_end.year - 1)
            period_label = f"{prev_start.strftime('%Y-%m')} vs {current_start.strftime('%Y-%m')}"
        else:
            # Month-over-month (mom): this month vs last month
            current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_end = now
            if now.month == 1:
                prev_start = now.replace(year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                prev_start = now.replace(month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_end = current_start
            period_label = f"{prev_start.strftime('%Y-%m')} vs {current_start.strftime('%Y-%m')}"

        # Fetch current period value
        current_val = await self._get_metric_value(metric, tenant_id, current_start, current_end)
        previous_val = await self._get_metric_value(metric, tenant_id, prev_start, prev_end)

        change = current_val - previous_val
        change_percent = round(change / previous_val * 100, 1) if previous_val != 0 else 0.0

        from app.schemas.dashboard import ComparisonData
        result = ComparisonData(
            current=current_val,
            previous=previous_val,
            change=round(change, 2),
            change_percent=change_percent,
            period_label=period_label,
        )
        return result.model_dump()

    async def _get_metric_value(
        self, metric: str, tenant_id: str, start: datetime, end: datetime
    ) -> float:
        """Helper: get a single numeric metric for a time range."""
        if metric == "candidates":
            val = await self.db.scalar(
                select(func.count()).select_from(Candidate).where(
                    Candidate.tenant_id == tenant_id,
                    Candidate.created_at >= start,
                    Candidate.created_at < end,
                )
            )
            return float(val or 0)
        elif metric == "interviews":
            val = await self.db.scalar(
                select(func.count()).select_from(Interview).where(
                    Interview.tenant_id == tenant_id,
                    Interview.created_at >= start,
                    Interview.created_at < end,
                )
            )
            return float(val or 0)
        elif metric == "offers":
            val = await self.db.scalar(
                select(func.count()).select_from(Offer).where(
                    Offer.tenant_id == tenant_id,
                    Offer.created_at >= start,
                    Offer.created_at < end,
                )
            )
            return float(val or 0)
        elif metric == "hires":
            val = await self.db.scalar(
                select(func.count()).select_from(Candidate).where(
                    Candidate.tenant_id == tenant_id,
                    Candidate.stage == "hired",
                    Candidate.updated_at >= start,
                    Candidate.updated_at < end,
                )
            )
            return float(val or 0)
        elif metric == "time_to_hire":
            rows = (await self.db.execute(
                select(Candidate.applied_at, Candidate.updated_at).where(
                    Candidate.tenant_id == tenant_id,
                    Candidate.stage == "hired",
                    Candidate.applied_at.isnot(None),
                    Candidate.updated_at >= start,
                    Candidate.updated_at < end,
                )
            )).all()
            if not rows:
                return 0.0
            days_list = [
                (r.updated_at - r.applied_at).days
                for r in rows if r.applied_at and r.updated_at
            ]
            return round(sum(days_list) / len(days_list), 1) if days_list else 0.0
        else:
            return 0.0

    async def get_position_metrics(
        self,
        tenant_id: str,
        position_id: UUID | None = None,
    ) -> list[dict]:
        """岗位级指标。

        Returns per-position metrics including resume count, match count,
        interview count, offer count, hire count, avg time-to-hire,
        match quality score, and conversion rate.

        Args:
            tenant_id: Tenant scope.
            position_id: Optional specific position; if None returns all.

        Returns:
            List of PositionMetrics dicts.
        """
        from app.schemas.dashboard import PositionMetrics
        from datetime import timezone

        # Build position query
        pos_query = select(Position).where(Position.tenant_id == tenant_id)
        if position_id:
            pos_query = pos_query.where(Position.id == position_id)
        positions = (await self.db.execute(
            pos_query.order_by(Position.created_at.desc()).limit(200)
        )).scalars().all()

        results = []
        for pos in positions:
            pid = pos.id

            # Resume count (candidates with applied stage)
            resume_count = await self.db.scalar(
                select(func.count()).select_from(Candidate).where(
                    Candidate.position_id == pid,
                    Candidate.status == "active",
                )
            ) or 0

            # Match count (candidates who were screened or further)
            match_count = await self.db.scalar(
                select(func.count()).select_from(Candidate).where(
                    Candidate.position_id == pid,
                    Candidate.status == "active",
                    Candidate.stage.in_(["screened", "interviewed", "offered", "hired"]),
                )
            ) or 0

            # Interview count
            interview_count = await self.db.scalar(
                select(func.count()).select_from(Interview).where(
                    Interview.position_id == pid,
                )
            ) or 0

            # Offer count
            offer_count = await self.db.scalar(
                select(func.count()).select_from(Offer).where(
                    Offer.position_id == pid,
                )
            ) or 0

            # Hire count
            hire_count = await self.db.scalar(
                select(func.count()).select_from(Candidate).where(
                    Candidate.position_id == pid,
                    Candidate.stage == "hired",
                )
            ) or 0

            # Avg time to hire
            hired_rows = (await self.db.execute(
                select(Candidate.applied_at, Candidate.updated_at).where(
                    Candidate.position_id == pid,
                    Candidate.stage == "hired",
                    Candidate.applied_at.isnot(None),
                )
            )).all()
            avg_tth = None
            if hired_rows:
                days_list = [
                    (r.updated_at - r.applied_at).days
                    for r in hired_rows if r.applied_at and r.updated_at
                ]
                if days_list:
                    avg_tth = round(sum(days_list) / len(days_list), 1)

            # Match quality score (average credibility of matched candidates)
            quality_score = None
            if match_count > 0:
                scores = (await self.db.execute(
                    select(func.avg(Candidate.credibility_score)).where(
                        Candidate.position_id == pid,
                        Candidate.status == "active",
                        Candidate.credibility_score.isnot(None),
                    )
                )).scalar()
                quality_score = round(float(scores), 1) if scores else None

            # Conversion rate: hires / resumes * 100
            conversion_rate = round(hire_count / resume_count * 100, 1) if resume_count > 0 else 0.0

            pm = PositionMetrics(
                position_id=pid,
                position_title=pos.title,
                resume_count=resume_count,
                match_count=match_count,
                interview_count=interview_count,
                offer_count=offer_count,
                hire_count=hire_count,
                avg_time_to_hire=avg_tth,
                match_quality_score=quality_score,
                conversion_rate=conversion_rate,
            )
            results.append(pm.model_dump())

        return results

    async def get_channel_roi(self, tenant_id: str) -> dict:
        """渠道ROI分析。

        Returns ROI analysis for each recruitment channel including
        cost per hire, conversion rate, time to hire, and quality indicators.
        """
        source_data = await self.get_source_effectiveness(tenant_id)

        # Cost per candidate by channel (placeholder values)
        cost_map = {
            "referral": 500,
            "boss": 200,
            "linkedin": 1500,
            "job_board": 300,
            "headhunter": 5000,
            "email": 50,
            "upload": 0,
            "social": 200,
            "campus": 400,
            "internal": 100,
        }

        roi_channels = []
        for source in source_data:
            src_name = source.get("source", "unknown")
            total = source.get("total", 0)
            hired = source.get("hired", 0)
            conversion_rate = source.get("conversion_rate", 0.0)

            cost_per_candidate = cost_map.get(src_name, 100)
            total_cost = cost_per_candidate * total
            cost_per_hire = (total_cost / hired) if hired > 0 else None

            # Time-to-hire per source (placeholder — would need actual data join)
            avg_tth_by_source = None

            # ROI score: higher is better — hired * 10000 / total_cost
            roi_score = round(
                (hired * 10000) / total_cost if total_cost > 0 else 0, 2
            )

            # Quality indicator: credibility score avg for this source
            avg_credibility = await self.db.scalar(
                select(func.avg(Candidate.credibility_score)).where(
                    Candidate.tenant_id == tenant_id,
                    Candidate.source == src_name,
                    Candidate.credibility_score.isnot(None),
                )
            )
            quality_indicator = round(float(avg_credibility), 1) if avg_credibility else None

            roi_channels.append({
                "source": src_name,
                "total_candidates": total,
                "hired": hired,
                "conversion_rate": conversion_rate,
                "cost_per_candidate": cost_per_candidate,
                "total_cost": total_cost,
                "cost_per_hire": cost_per_hire,
                "avg_time_to_hire": avg_tth_by_source,
                "quality_indicator": quality_indicator,
                "roi_score": roi_score,
            })

        # Sort by ROI score descending
        roi_channels.sort(key=lambda x: x["roi_score"], reverse=True)
        return {"channels": roi_channels}

    async def get_time_efficiency(self, tenant_id: str) -> dict:
        """招聘时间效率分析。

        Analyzes time spent in each pipeline stage, identifies bottlenecks,
        and returns efficiency metrics.
        """
        from datetime import timezone

        # Get all hired candidates with timestamps
        hired_rows = (await self.db.execute(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "hired",
                Candidate.applied_at.isnot(None),
            )
        )).scalars().all()

        total_hired = len(hired_rows)
        if total_hired == 0:
            return {
                "total_hired": 0,
                "avg_total_days": 0,
                "stage_durations": {},
                "efficiency_score": None,
                "bottleneck_stage": None,
            }

        # Compute stage durations (mock — using applied_at to updated_at as total)
        total_days_list = []
        for c in hired_rows:
            if c.applied_at and c.updated_at:
                total_days_list.append((c.updated_at - c.applied_at).days)

        avg_total_days = round(sum(total_days_list) / len(total_days_list), 1) if total_days_list else 0.0

        # Stage duration breakdown (mock realistic values)
        # In production, would need stage transition timestamps
        stage_durations = {
            "applied_to_screened": round(avg_total_days * 0.15, 1),
            "screened_to_interviewed": round(avg_total_days * 0.25, 1),
            "interviewed_to_offered": round(avg_total_days * 0.35, 1),
            "offered_to_hired": round(avg_total_days * 0.25, 1),
        }

        # Identify bottleneck (longest stage)
        bottleneck_stage = max(stage_durations.keys(), key=lambda k: stage_durations[k] or 0)

        # Efficiency score: benchmark is 30 days; lower is better
        benchmark_days = 30.0
        if avg_total_days <= benchmark_days:
            efficiency_score = round(100 - (avg_total_days / benchmark_days) * 20, 1)
        else:
            efficiency_score = max(0, round(100 - ((avg_total_days - benchmark_days) / benchmark_days) * 50, 1))

        # Distribution by time bracket
        brackets = {
            "under_15_days": sum(1 for d in total_days_list if d < 15),
            "15_to_30_days": sum(1 for d in total_days_list if 15 <= d < 30),
            "30_to_60_days": sum(1 for d in total_days_list if 30 <= d < 60),
            "over_60_days": sum(1 for d in total_days_list if d >= 60),
        }

        return {
            "total_hired": total_hired,
            "avg_total_days": avg_total_days,
            "median_days": sorted(total_days_list)[len(total_days_list) // 2] if total_days_list else 0,
            "stage_durations": stage_durations,
            "bottleneck_stage": bottleneck_stage,
            "efficiency_score": efficiency_score,
            "time_distribution": brackets,
            "recommendation": (
                f"招聘平均耗时{avg_total_days}天，瓶颈阶段为{bottleneck_stage}。"
                f"建议优化该阶段的流程以提升整体效率。"
            ),
        }

    # ══════════════════════════════════════════════════════════════════
    # M8: Funnel Comparison, Trend Prediction, Position Analytics
    # ══════════════════════════════════════════════════════════════════

    async def get_funnel_comparison(
        self,
        position_id: UUID | None,
        period: str,
        compare_with: str,
        tenant_id: str,
    ) -> dict:
        """漏斗同比环比分析。

        Args:
            position_id: Optional position filter.
            period: Base period (daily/weekly/monthly).
            compare_with: Comparison target — last_week / last_month / last_year.
            tenant_id: Tenant scope.

        Returns:
            FunnelComparisonResponse dict.
        """
        from datetime import timedelta, timezone
        from app.schemas.dashboard import (
            FunnelResponse,
            FunnelStage,
            FunnelComparisonResponse,
            ComparisonData,
        )

        now = datetime.now(timezone.utc)

        # Determine current and previous date ranges
        if compare_with == "last_week":
            current_start = now - timedelta(weeks=1)
            current_end = now
            prev_start = current_start - timedelta(weeks=1)
            prev_end = current_start
            period_label = "vs上周"
        elif compare_with == "last_year":
            current_start = now - timedelta(days=365)
            current_end = now
            prev_start = current_start.replace(year=current_start.year - 1)
            prev_end = current_start
            period_label = "vs去年"
        else:
            # Default: last_month
            current_start = now - timedelta(days=30)
            current_end = now
            prev_start = current_start - timedelta(days=30)
            prev_end = current_start
            period_label = "vs上月"

        # Fetch funnel for current period
        current_funnel_data = await self._build_funnel(
            tenant_id, position_id, current_start.date(), current_end.date()
        )

        # Fetch funnel for comparison period
        prev_funnel_data = await self._build_funnel(
            tenant_id, position_id, prev_start.date(), prev_end.date()
        )

        # Calculate overall conversion for comparison
        current_hires = sum(
            s.count for s in current_funnel_data if s.stage == "hired"
        )
        prev_hires = sum(
            s.count for s in prev_funnel_data if s.stage == "hired"
        )
        current_total = sum(s.count for s in current_funnel_data) or 1
        prev_total = sum(s.count for s in prev_funnel_data) or 1
        current_rate = current_hires / current_total * 100
        prev_rate = prev_hires / prev_total * 100

        change = current_rate - prev_rate
        change_pct = round(change / prev_rate * 100, 1) if prev_rate != 0 else 0.0

        current_resp = FunnelResponse(
            position_id=position_id,
            stages=current_funnel_data,
            period=period,
            generated_at=now,
        )
        comparison = ComparisonData(
            current=round(current_rate, 2),
            previous=round(prev_rate, 2),
            change=round(change, 2),
            change_percent=change_pct,
            period_label=period_label,
        )
        result = FunnelComparisonResponse(
            current=current_resp,
            comparison=comparison,
            comparison_period=compare_with,
        )
        return result.model_dump()

    async def _build_funnel(
        self,
        tenant_id: str,
        position_id: UUID | None,
        date_from: date,
        date_to: date,
    ) -> list:
        """Helper: build funnel stages for a date range."""
        from app.schemas.dashboard import FunnelStage

        query = (
            select(Candidate.stage, func.count().label("count"))
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
            )
            .group_by(Candidate.stage)
        )
        if position_id:
            query = query.where(Candidate.position_id == position_id)
        query = query.where(Candidate.applied_at >= date_from)
        query = query.where(Candidate.applied_at < date_to)

        rows = (await self.db.execute(query)).all()
        stage_counts = {row.stage: row.count for row in rows}

        ordered_stages = ["applied", "screened", "interviewed", "offered", "hired"]
        stages = []
        first_count = None
        for s in ordered_stages:
            count = stage_counts.get(s, 0)
            if first_count is None and count > 0:
                first_count = count
            conv = round(count / stages[-1].count * 100, 1) if stages and stages[-1].count > 0 else None
            cum = round(count / first_count * 100, 1) if first_count and first_count > 0 else None
            stages.append(FunnelStage(
                stage=s,
                label=s,
                count=count,
                conversion_rate=conv,
                cumulative_rate=cum,
            ))
        return stages

    async def get_trend_prediction(
        self,
        period: str,
        weeks_ahead: int,
        tenant_id: str,
    ) -> dict:
        """趋势预测 — 简单线性回归。

        Uses recent historical data to predict future N weeks' trends
        with confidence intervals based on residual variance.

        Args:
            period: Grouping (daily/weekly/monthly).
            weeks_ahead: Number of weeks to predict.
            tenant_id: Tenant scope.

        Returns:
            TrendPredictionResponse dict.
        """
        from datetime import timedelta, timezone
        from app.schemas.dashboard import TrendDataPoint, PredictionPoint, TrendPredictionResponse

        now = datetime.now(timezone.utc)

        # Fetch last 12 weeks of data
        lookback_start = now - timedelta(weeks=12)
        query = (
            select(
                func.date_trunc("week", Candidate.created_at).label("week"),
                func.count().label("cnt"),
            )
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.created_at >= lookback_start,
            )
            .group_by("week")
            .order_by("week")
        )
        rows = (await self.db.execute(query)).all()

        # Build actual data points
        actual_points = []
        for r in rows:
            week_label = r.week.strftime("%Y-W%W") if r.week else "unknown"
            actual_points.append(TrendDataPoint(
                date=week_label,
                resumes=r.cnt,
                matches=0,
                interviews=0,
                offers=0,
                hires=0,
            ))

        # Simple linear regression on resume counts
        n = len(actual_points)
        if n >= 2:
            xs = list(range(n))
            ys = [p.resumes for p in actual_points]
            x_mean = sum(xs) / n
            y_mean = sum(ys) / n
            ss_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
            ss_xx = sum((x - x_mean) ** 2 for x in xs)
            slope = ss_xy / ss_xx if ss_xx != 0 else 0
            intercept = y_mean - slope * x_mean

            # Residual variance for confidence interval
            residuals = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
            residual_var = sum(r ** 2 for r in residuals) / max(n - 2, 1)
            import math
            std_err = math.sqrt(residual_var) if residual_var > 0 else 1.0
            z = 1.96  # 95% confidence

            # Generate predictions
            predicted_points = []
            for i in range(weeks_ahead):
                x_pred = n + i
                pred_val = slope * x_pred + intercept
                pred_val = max(0, pred_val)
                # Future week date
                pred_date = (now + timedelta(weeks=i + 1)).strftime("%Y-W%W")
                predicted_points.append(PredictionPoint(
                    date=pred_date,
                    predicted=round(pred_val, 1),
                    confidence_lower=round(max(0, pred_val - z * std_err), 1),
                    confidence_upper=round(pred_val + z * std_err, 1),
                ))

            # Confidence score: based on R²
            ss_tot = sum((y - y_mean) ** 2 for y in ys)
            r_squared = 1 - (residual_var * (n - 2)) / ss_tot if ss_tot > 0 else 0
            confidence = round(max(0, min(1, r_squared)), 3)
        else:
            # Not enough data — flat prediction
            predicted_points = []
            last_val = actual_points[-1].resumes if actual_points else 0
            for i in range(weeks_ahead):
                pred_date = (now + timedelta(weeks=i + 1)).strftime("%Y-W%W")
                predicted_points.append(PredictionPoint(
                    date=pred_date,
                    predicted=float(last_val),
                    confidence_lower=0.0,
                    confidence_upper=float(last_val * 2),
                ))
            confidence = 0.1

        result = TrendPredictionResponse(
            actual=actual_points,
            predicted=predicted_points,
            method="linear_regression",
            confidence=confidence,
        )
        return result.model_dump()

    async def get_position_analytics(
        self,
        position_id: UUID,
        tenant_id: str,
    ) -> dict:
        """岗位级完整分析。

        Returns a comprehensive analysis for a single position:
        - Full funnel with conversion rates
        - Average match score (credibility)
        - Average time to hire
        - Interview pass rate
        - Offer accept rate
        """
        from datetime import timezone
        from app.schemas.dashboard import (
            FunnelResponse,
            FunnelStage,
            PositionAnalytics,
        )

        # Get position info
        pos = await self.db.scalar(
            select(Position).where(
                Position.id == position_id,
                Position.tenant_id == tenant_id,
            )
        )
        if pos is None:
            return {"error": "Position not found", "position_id": str(position_id)}

        # Build funnel for this position
        funnel_query = (
            select(Candidate.stage, func.count().label("count"))
            .where(
                Candidate.position_id == position_id,
                Candidate.status == "active",
            )
            .group_by(Candidate.stage)
        )
        funnel_rows = (await self.db.execute(funnel_query)).all()
        stage_counts = {row.stage: row.count for row in funnel_rows}

        ordered_stages = ["applied", "screened", "interviewed", "offered", "hired"]
        stages = []
        first_count = None
        for s in ordered_stages:
            count = stage_counts.get(s, 0)
            if first_count is None and count > 0:
                first_count = count
            conv = round(count / stages[-1].count * 100, 1) if stages and stages[-1].count > 0 else None
            cum = round(count / first_count * 100, 1) if first_count and first_count > 0 else None
            stages.append(FunnelStage(
                stage=s, label=s, count=count,
                conversion_rate=conv, cumulative_rate=cum,
            ))

        now_dt = datetime.now(timezone.utc)
        funnel_resp = FunnelResponse(
            position_id=position_id,
            stages=stages,
            period="all",
            generated_at=now_dt,
        )

        # Average match score (credibility)
        avg_cred = await self.db.scalar(
            select(func.avg(Candidate.credibility_score)).where(
                Candidate.position_id == position_id,
                Candidate.credibility_score.isnot(None),
            )
        )
        avg_match_score = round(float(avg_cred), 1) if avg_cred else 0.0

        # Average time to hire
        hired_rows = (await self.db.execute(
            select(Candidate.applied_at, Candidate.updated_at).where(
                Candidate.position_id == position_id,
                Candidate.stage == "hired",
                Candidate.applied_at.isnot(None),
            )
        )).all()
        if hired_rows:
            days_list = [
                (r.updated_at - r.applied_at).days
                for r in hired_rows if r.applied_at and r.updated_at
            ]
            avg_tth = round(sum(days_list) / len(days_list), 1) if days_list else None
        else:
            avg_tth = None

        # Interview pass rate
        total_interviews = await self.db.scalar(
            select(func.count()).select_from(Interview).where(
                Interview.position_id == position_id,
            )
        ) or 0
        passed_interviews = await self.db.scalar(
            select(func.count()).select_from(Interview).where(
                Interview.position_id == position_id,
                Interview.recommendation.in_(["strong_yes", "yes"]),
            )
        ) or 0
        interview_pass_rate = round(passed_interviews / total_interviews * 100, 1) if total_interviews > 0 else 0.0

        # Offer accept rate
        total_offers = await self.db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.position_id == position_id,
            )
        ) or 0
        accepted_offers = await self.db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.position_id == position_id,
                Offer.status == "accepted",
            )
        ) or 0
        offer_accept_rate = round(accepted_offers / total_offers * 100, 1) if total_offers > 0 else 0.0

        result = PositionAnalytics(
            position_id=position_id,
            position_title=pos.title,
            funnel=funnel_resp,
            avg_match_score=avg_match_score,
            avg_time_to_hire=avg_tth,
            interview_pass_rate=interview_pass_rate,
            offer_accept_rate=offer_accept_rate,
        )
        return result.model_dump()

    async def get_channel_roi_enhanced(
        self,
        tenant_id: str,
        date_from: str | None,
        date_to: str | None,
    ) -> dict:
        """渠道ROI增强版。

        Enhanced Channel ROI with date filtering and structured
        output matching the ChannelROI schema.

        Args:
            tenant_id: Tenant scope.
            date_from: Optional start date (YYYY-MM-DD).
            date_to: Optional end date (YYYY-MM-DD).

        Returns:
            Dict with list of ChannelROI data.
        """
        from app.schemas.dashboard import ChannelROI

        # Build base query
        cand_query = (
            select(
                Candidate.source,
                func.count().label("total"),
                func.count(
                    case((Candidate.stage.in_(["interviewed", "offered", "hired"]), Candidate.id))
                ).label("interviewed"),
                func.count(
                    case((Candidate.stage.in_(["offered", "hired"]), Candidate.id))
                ).label("offered"),
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

        if date_from:
            cand_query = cand_query.where(Candidate.applied_at >= date_from)
        if date_to:
            cand_query = cand_query.where(Candidate.applied_at < date_to)

        rows = (await self.db.execute(cand_query)).all()

        # Cost per candidate by channel (placeholder)
        cost_map = {
            "referral": 500, "boss": 200, "linkedin": 1500,
            "job_board": 300, "headhunter": 5000, "email": 50,
            "upload": 0, "social": 200, "campus": 400, "internal": 100,
        }

        channels = []
        for row in rows:
            src = row.source or "unknown"
            total = row.total
            interviewed = row.interviewed
            offered = row.offered
            hired = row.hired
            cost_per = cost_map.get(src, 100)
            total_cost = cost_per * total
            cph = round(total_cost / hired, 2) if hired > 0 else None
            roi = round((hired * 10000) / total_cost, 2) if total_cost > 0 else 0.0

            channels.append(ChannelROI(
                channel=src,
                resumes=total,
                interviews=interviewed,
                offers=offered,
                hires=hired,
                cost=float(total_cost) if total_cost > 0 else None,
                cost_per_hire=cph,
                roi_score=roi,
            ))

        channels.sort(key=lambda x: x.roi_score, reverse=True)
        return {"channels": [c.model_dump() for c in channels]}
