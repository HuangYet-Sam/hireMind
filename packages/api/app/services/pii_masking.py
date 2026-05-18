"""
PII Masking Service — automatically masks sensitive information before
LLM calls and restores it afterwards.

Masking rules:
- Chinese names (2-4 chars) / English names (First Last) → [NAME_N]
- Phone numbers (Chinese mobile formats) → [PHONE_N]
- Email addresses → [EMAIL_N]
- Chinese ID card numbers (18-digit) → [ID_CARD_N]
- Chinese addresses → [ADDRESS_N]

Security:
- Mapping table lives in memory only, returned to caller for safekeeping.
- Audit log emitted per mask/unmask operation (never includes original PII).
- Thread-safe: all state is local to each method call.
"""

import logging
import re
from typing import Any

logger = logging.getLogger("hiremind.pii_masking")

# ── Chinese character utilities ──────────────────────────────────────────

_IS_CN = re.compile(r"[一-鿿]")

_SINGLE_SURNAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许"
    "何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章"
    "云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳"
    "鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐"
    "于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚"
    "邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊"
    "纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江"
    "童颜郭梅盛林刁钟徐丘骆高夏蔡田樊胡凌霍万"
    "支柯管卢莫经房干解应宗丁宣邓郁单杭洪包诸"
    "左石崔吉龚程邢裴陆荣翁荀羊甄曲家封储靳邴"
    "段富巫乌焦巴牧山谷车侯蓬全班仰秋仲伊宫宁"
    "仇栾暴甘戎祖武符刘景詹束龙叶幸司黎蒲边温"
    "庄晏柴瞿阎充慕连茹习艾鱼容向古易廖庾居衡"
    "步都耿满匡国文寇广东欧聂敖冷辛简饶空曾沙"
    "养丰巢关查后红游权盖益桓公"
)

_SURNAME_SET = set(_SINGLE_SURNAMES)

# Characters that are both surnames AND common function words.
# When these follow a name candidate, treat as boundary rather than continuation.
_AMBIGUOUS_BOUNDARY = frozenset("和与及也都被把让给在是从")

_COMPOUND_SURNAMES = (
    "欧阳", "司马", "上官", "诸葛", "夏侯", "皇甫",
    "尉迟", "公孙", "令狐", "宇文", "长孙", "慕容",
    "端木", "司空", "东方", "南宫", "西门", "百里",
)

# ── Chinese name context detection ───────────────────────────────────────

_NAME_KEYWORDS = frozenset({
    "姓名", "名字", "叫", "联系", "候选", "员工", "经理", "同事",
    "主管", "总监", "负责", "应聘", "申请", "用户", "客户",
    "先生", "女士", "老师", "教授", "介绍", "推荐",
})

_NAME_SEPARATORS = frozenset("和与、，, \t\n")

_POST_NAME_CHARS = frozenset("的了是在有和与及也都将或但是不被把让给，。、；：！？\n\r\t ")

_PERSON_SUFFIXES = ("人", "员", "者")
_KW_SEPARATORS = ("：", ":", " ")


def _is_name_context(text: str, start: int, end: int) -> bool:
    for kw in _NAME_KEYWORDS:
        if start >= len(kw) and text[start - len(kw):start] == kw:
            return True
        for ps in _PERSON_SUFFIXES:
            full = kw + ps
            if start >= len(full) and text[start - len(full):start] == full:
                return True
        for sep in _KW_SEPARATORS:
            full = kw + sep
            if start >= len(full) and text[start - len(full):start] == full:
                return True
        for ps in _PERSON_SUFFIXES:
            for sep in _KW_SEPARATORS:
                full = kw + ps + sep
                if start >= len(full) and text[start - len(full):start] == full:
                    return True

    if start > 0 and text[start - 1] in _NAME_SEPARATORS:
        return True

    if start == 0:
        if end == len(text):
            return True
        if text[end] in _POST_NAME_CHARS or not _IS_CN.match(text[end]):
            return True

    if start > 0 and not _IS_CN.match(text[start - 1]):
        return True

    return False


def _scan_chinese_names(text: str) -> list[tuple[int, int, str]]:
    """Scan text for Chinese names using a shortest-first strategy."""
    names: list[tuple[int, int, str]] = []
    i = 0
    while i < len(text):
        matched = False

        # Try compound surname first (longer prefix wins)
        for cs in _COMPOUND_SURNAMES:
            cs_len = len(cs)
            if text[i:i + cs_len] == cs:
                for given_len in range(1, 3):
                    end = i + cs_len + given_len
                    if end > len(text):
                        continue
                    post = text[end] if end < len(text) else None
                    if post is not None and post in _SURNAME_SET and post not in _AMBIGUOUS_BOUNDARY:
                        continue
                    if _is_name_context(text, i, end):
                        names.append((i, end, text[i:end]))
                        i = end
                        matched = True
                        break
                if not matched:
                    i += 1
                matched = True
                break

        if matched:
            continue

        # Single-char surname
        if text[i] in _SURNAME_SET:
            for given_len in range(1, 4):
                end = i + 1 + given_len
                if end > len(text):
                    continue
                post = text[end] if end < len(text) else None
                if post is not None and post in _SURNAME_SET and post not in _AMBIGUOUS_BOUNDARY:
                    continue
                if _is_name_context(text, i, end):
                    names.append((i, end, text[i:end]))
                    i = end
                    matched = True
                    break
            if not matched:
                i += 1
        else:
            i += 1

    return names


# ── English name detection ───────────────────────────────────────────────

RE_CAP_WORD = re.compile(r"\b[A-Z][a-z]{1,20}\b")

_EN_EXCLUDE = frozenset({
    "The", "This", "That", "These", "Those", "A", "An",
    "Candidate", "Employee", "Manager", "Director", "Contact",
    "Address", "Phone", "Email", "Position", "Company",
    "Department", "Title", "Senior", "Junior", "Lead", "Chief",
    "Head", "About", "From", "With", "For", "And", "But", "Not",
    "Has", "Have", "Had", "Was", "Were", "Will", "Would", "Could",
    "Should", "New", "Old", "Good", "Best", "Mr", "Mrs", "Ms",
    "Dr", "Prof", "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday", "January", "February", "March",
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "Thank", "Please", "Hello",
    "Dear", "Thanks", "Yes", "No", "Applied", "Resigned",
    "Joined", "Left", "Worked", "Currently", "Previously",
    "Attached", "Below", "Above", "Here", "There",
})


def _find_english_names(text: str) -> list[tuple[int, int, str]]:
    caps = [(m.start(), m.end(), m.group(0)) for m in RE_CAP_WORD.finditer(text)]
    names: list[tuple[int, int, str]] = []
    i = 0
    while i < len(caps):
        if i + 1 < len(caps):
            curr_end, next_start = caps[i][1], caps[i + 1][0]
            if next_start == curr_end + 1 and text[curr_end] == " ":
                first, second = caps[i][2], caps[i + 1][2]
                if first not in _EN_EXCLUDE and second not in _EN_EXCLUDE:
                    names.append((caps[i][0], caps[i + 1][1], f"{first} {second}"))
                    i += 2
                    continue
                if first in _EN_EXCLUDE and i + 2 < len(caps):
                    gap = caps[i + 1][1]
                    if caps[i + 2][0] == gap + 1 and text[gap] == " ":
                        third = caps[i + 2][2]
                        if second not in _EN_EXCLUDE and third not in _EN_EXCLUDE:
                            names.append((caps[i + 1][0], caps[i + 2][1], f"{second} {third}"))
                            i += 3
                            continue
        i += 1
    return names


# ── Other PII regex patterns ─────────────────────────────────────────────

RE_PHONE = re.compile(
    r"(?<!\d)(?:\+86[-\s]?)?1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}(?!\d)"
)

RE_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

RE_ID_CARD = re.compile(
    r"(?<!\d)"
    r"[1-9]\d{5}(?:19|20)\d{2}"
    r"(?:0[1-9]|1[0-2])"
    r"(?:0[1-9]|[12]\d|3[01])"
    r"\d{3}[\dXx]"
    r"(?!\d)"
)

RE_ADDRESS = re.compile(
    r"(?:"
    r"[一-鿿]{2,5}(?:省|自治区|特别行政区)"
    r"|[一-鿿]{2,4}市"
    r"|[一-鿿]{2,5}(?:区|县|旗)"
    r")"
    r"[一-鿿0-9A-Za-z\-#号栋幢楼室单元层街道巷弄胡同路村组乡镇]{3,80}"
)

_PII_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("ID_CARD", RE_ID_CARD),
    ("PHONE", RE_PHONE),
    ("EMAIL", RE_EMAIL),
    ("ADDRESS", RE_ADDRESS),
]


class PIIMaskingService:
    """Stateless PII masking/unmasking service. Thread-safe by design."""

    async def mask(self, text: str) -> tuple[str, dict[str, str]]:
        """Mask PII in *text*. Returns (masked_text, mapping)."""
        if not text:
            return text, {}

        mapping: dict[str, str] = {}
        counters: dict[str, int] = {}
        result = text

        for pii_type, pattern in _PII_RULES:
            result = self._regex_mask(result, pii_type, pattern, mapping, counters)

        result = self._apply_name_spans(result, _scan_chinese_names(result), mapping, counters)
        result = self._apply_name_spans(result, _find_english_names(result), mapping, counters)

        logger.info("pii_mask_completed total_masks=%d", len(mapping))
        return result, mapping

    async def unmask(self, text: str, mapping: dict[str, str]) -> str:
        """Restore original PII values in *text* using *mapping*."""
        if not text or not mapping:
            return text
        result = text
        for placeholder, original in mapping.items():
            result = result.replace(placeholder, original)
        logger.info("pii_unmask_completed restored=%d", len(mapping))
        return result

    async def mask_dict(
        self, data: dict[str, Any], fields: list[str]
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Mask PII in the specified *fields* of *data* (on a copy)."""
        combined: dict[str, str] = {}
        result = dict(data)
        for field in fields:
            value = result.get(field)
            if isinstance(value, str) and value:
                masked, m = await self.mask(value)
                result[field] = masked
                combined.update(m)
            elif isinstance(value, dict):
                masked, m = await self._mask_nested_dict(value)
                result[field] = masked
                combined.update(m)
        return result, combined

    # ── Internal helpers ────────────────────────────────────────────────

    @staticmethod
    def _regex_mask(
        text: str,
        pii_type: str,
        pattern: re.Pattern[str],
        mapping: dict[str, str],
        counters: dict[str, int],
    ) -> str:
        seen: dict[str, str] = {}

        def replacer(m: re.Match[str]) -> str:
            original = m.group(0)
            if original in seen:
                return seen[original]
            idx = counters.get(pii_type, 0) + 1
            counters[pii_type] = idx
            placeholder = f"[{pii_type}_{idx}]"
            mapping[placeholder] = original
            seen[original] = placeholder
            return placeholder

        return pattern.sub(replacer, text)

    @staticmethod
    def _apply_name_spans(
        text: str,
        spans: list[tuple[int, int, str]],
        mapping: dict[str, str],
        counters: dict[str, int],
    ) -> str:
        if not spans:
            return text

        seen: dict[str, str] = {}
        parts: list[str] = []
        last_end = 0

        for start, end, original in spans:
            if start < last_end:
                continue
            parts.append(text[last_end:start])
            if original in seen:
                parts.append(seen[original])
            else:
                idx = counters.get("NAME", 0) + 1
                counters["NAME"] = idx
                ph = f"[NAME_{idx}]"
                mapping[ph] = original
                seen[original] = ph
                parts.append(ph)
            last_end = end

        parts.append(text[last_end:])
        return "".join(parts)

    async def _mask_nested_dict(
        self, data: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, str]]:
        combined: dict[str, str] = {}
        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str) and value:
                masked, m = await self.mask(value)
                result[key] = masked
                combined.update(m)
            elif isinstance(value, dict):
                masked, m = await self._mask_nested_dict(value)
                result[key] = masked
                combined.update(m)
            else:
                result[key] = value
        return result, combined
