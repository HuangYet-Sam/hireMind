"""
Unit tests for PII Masking Service.

Covers: Chinese/English name masking, phone masking (incl. international),
email masking, ID card masking, address masking, unmasking, dict masking,
concurrent safety, edge cases, and mapping isolation.
"""

import asyncio

import pytest

from app.services.pii_masking import PIIMaskingService


@pytest.fixture
def service():
    return PIIMaskingService()


# ── Chinese Name Masking ──────────────────────────────────────────────────


class TestChineseNameMasking:

    @pytest.mark.asyncio
    async def test_single_char_surname_two_char_name(self, service):
        text = "候选人张三的简历"
        masked, mapping = await service.mask(text)
        assert "张三" not in masked
        assert any(v == "张三" for v in mapping.values())

    @pytest.mark.asyncio
    async def test_single_char_surname_three_char_name(self, service):
        text = "联系人王小明的电话"
        masked, mapping = await service.mask(text)
        assert "王小明" not in masked
        assert any(v == "王小明" for v in mapping.values())

    @pytest.mark.asyncio
    async def test_single_char_surname_four_char_name(self, service):
        text = "经理司马懿的项目"
        masked, mapping = await service.mask(text)
        assert "司马懿" not in masked

    @pytest.mark.asyncio
    async def test_compound_surname(self, service):
        text = "员工欧阳明的报告"
        masked, mapping = await service.mask(text)
        assert "欧阳明" not in masked
        assert any(v == "欧阳明" for v in mapping.values())

    @pytest.mark.asyncio
    async def test_multiple_chinese_names(self, service):
        text = "张三和李四共同完成"
        masked, mapping = await service.mask(text)
        assert "张三" not in masked
        assert "李四" not in masked
        assert any(v == "张三" for v in mapping.values())
        assert any(v == "李四" for v in mapping.values())

    @pytest.mark.asyncio
    async def test_chinese_name_standalone(self, service):
        text = "张三"
        masked, mapping = await service.mask(text)
        assert "张三" not in masked
        assert "[NAME_1]" in masked
        assert mapping.get("[NAME_1]") == "张三"


# ── English Name Masking ──────────────────────────────────────────────────


class TestEnglishNameMasking:

    @pytest.mark.asyncio
    async def test_basic_english_name(self, service):
        text = "Candidate John Smith applied"
        masked, mapping = await service.mask(text)
        assert "John Smith" not in masked
        assert any(v == "John Smith" for v in mapping.values())

    @pytest.mark.asyncio
    async def test_english_name_three_parts(self, service):
        text = "Employee John David Brown resigned"
        masked, mapping = await service.mask(text)
        assert "John David Brown" not in masked

    @pytest.mark.asyncio
    async def test_multiple_english_names(self, service):
        text = "Alice Johnson and Bob Williams"
        masked, mapping = await service.mask(text)
        assert "Alice Johnson" not in masked
        assert "Bob Williams" not in masked
        assert any(v == "Alice Johnson" for v in mapping.values())
        assert any(v == "Bob Williams" for v in mapping.values())


# ── Phone Number Masking ──────────────────────────────────────────────────


class TestPhoneMasking:

    @pytest.mark.asyncio
    async def test_plain_11_digit(self, service):
        text = "电话13812345678"
        masked, mapping = await service.mask(text)
        assert "13812345678" not in masked
        assert any(v == "13812345678" for v in mapping.values())

    @pytest.mark.asyncio
    async def test_dashed_format(self, service):
        text = "手机号138-1234-5678"
        masked, mapping = await service.mask(text)
        assert "138-1234-5678" not in masked
        assert any(v == "138-1234-5678" for v in mapping.values())

    @pytest.mark.asyncio
    async def test_international_plus86(self, service):
        text = "电话+8613812345678"
        masked, mapping = await service.mask(text)
        assert "13812345678" not in masked or "+8613812345678" not in masked

    @pytest.mark.asyncio
    async def test_international_plus86_space(self, service):
        text = "联系方式 +86 138 1234 5678"
        masked, mapping = await service.mask(text)
        assert "13812345678" not in masked.replace(" ", "").replace("+86", "")

    @pytest.mark.asyncio
    async def test_multiple_phones(self, service):
        text = "主号13900001111 备用15022223333"
        masked, mapping = await service.mask(text)
        assert "13900001111" not in masked
        assert "15022223333" not in masked

    @pytest.mark.asyncio
    async def test_different_prefixes(self, service):
        for prefix in ["130", "150", "170", "180", "199"]:
            text = f"号码{prefix}12345678"
            masked, _ = await service.mask(text)
            assert f"{prefix}12345678" not in masked


# ── Email Masking ─────────────────────────────────────────────────────────


class TestEmailMasking:

    @pytest.mark.asyncio
    async def test_basic_email(self, service):
        text = "邮箱test@example.com"
        masked, mapping = await service.mask(text)
        assert "test@example.com" not in masked
        assert any(v == "test@example.com" for v in mapping.values())

    @pytest.mark.asyncio
    async def test_email_with_dots(self, service):
        text = "联系 first.last@company.co.uk"
        masked, mapping = await service.mask(text)
        assert "first.last@company.co.uk" not in masked

    @pytest.mark.asyncio
    async def test_multiple_emails(self, service):
        text = "工作邮箱a@b.com和c@d.org"
        masked, mapping = await service.mask(text)
        assert "a@b.com" not in masked
        assert "c@d.org" not in masked


# ── ID Card Masking ───────────────────────────────────────────────────────


class TestIdCardMasking:

    @pytest.mark.asyncio
    async def test_standard_18_digit(self, service):
        text = "身份证号110101199003077733"
        masked, mapping = await service.mask(text)
        assert "110101199003077733" not in masked
        assert any(v == "110101199003077733" for v in mapping.values())

    @pytest.mark.asyncio
    async def test_id_card_ending_x(self, service):
        text = "证件号码44030519881212001X"
        masked, mapping = await service.mask(text)
        assert "44030519881212001X" not in masked

    @pytest.mark.asyncio
    async def test_id_card_ending_lowercase_x(self, service):
        text = "证件号32010219950101123x"
        masked, mapping = await service.mask(text)
        assert "32010219950101123x" not in masked


# ── Address Masking ───────────────────────────────────────────────────────


class TestAddressMasking:

    @pytest.mark.asyncio
    async def test_province_level_address(self, service):
        text = "住址广东省深圳市南山区科技路1号"
        masked, mapping = await service.mask(text)
        assert "广东省" not in masked or "深圳市南山区科技路1号" not in masked

    @pytest.mark.asyncio
    async def test_city_level_address(self, service):
        text = "地址北京市朝阳区建国路88号"
        masked, mapping = await service.mask(text)
        assert "北京市朝阳区建国路88号" not in masked

    @pytest.mark.asyncio
    async def test_district_level_address(self, service):
        text = "住在浦东新区陆家嘴环路1000号"
        masked, mapping = await service.mask(text)
        assert "浦东新区陆家嘴环路1000号" not in masked


# ── Unmask (Restore) ─────────────────────────────────────────────────────


class TestUnmask:

    @pytest.mark.asyncio
    async def test_unmask_single_type(self, service):
        original = "电话13812345678"
        masked, mapping = await service.mask(original)
        restored = await service.unmask(masked, mapping)
        assert restored == original

    @pytest.mark.asyncio
    async def test_unmask_mixed_types(self, service):
        original = "张三的电话是13812345678，邮箱test@example.com"
        masked, mapping = await service.mask(original)
        restored = await service.unmask(masked, mapping)
        assert restored == original

    @pytest.mark.asyncio
    async def test_unmask_empty_mapping(self, service):
        text = "没有敏感信息"
        restored = await service.unmask(text, {})
        assert restored == text

    @pytest.mark.asyncio
    async def test_unmask_empty_text(self, service):
        restored = await service.unmask("", {"[NAME_1]": "张三"})
        assert restored == ""

    @pytest.mark.asyncio
    async def test_unmask_roundtrip_full(self, service):
        original = (
            "姓名：张三，英文名 David Chen，手机138-1234-5678，"
            "身份证110101199003077733，邮箱zs@test.com，"
            "地址北京市海淀区中关村大街1号"
        )
        masked, mapping = await service.mask(original)
        restored = await service.unmask(masked, mapping)
        assert restored == original

    @pytest.mark.asyncio
    async def test_unmask_100_percent_accuracy(self, service):
        """Every original value must be exactly restored."""
        original = "张三13812345678test@example.com110101199003077733"
        masked, mapping = await service.mask(original)
        restored = await service.unmask(masked, mapping)
        assert restored == original


# ── Dict Masking ──────────────────────────────────────────────────────────


class TestMaskDict:

    @pytest.mark.asyncio
    async def test_mask_specified_fields(self, service):
        data = {
            "name": "张三",
            "phone": "13812345678",
            "city": "北京",
        }
        masked_data, mapping = await service.mask_dict(data, ["name", "phone"])
        assert masked_data["city"] == "北京"
        assert "张三" not in masked_data["name"]
        assert "13812345678" not in masked_data["phone"]

    @pytest.mark.asyncio
    async def test_mask_dict_preserves_non_string(self, service):
        data = {"name": "张三", "age": 30, "active": True}
        masked_data, _ = await service.mask_dict(data, ["name"])
        assert masked_data["age"] == 30
        assert masked_data["active"] is True

    @pytest.mark.asyncio
    async def test_mask_dict_missing_field(self, service):
        data = {"name": "张三"}
        masked_data, mapping = await service.mask_dict(data, ["phone"])
        assert masked_data["name"] == "张三"
        assert len(mapping) == 0

    @pytest.mark.asyncio
    async def test_mask_dict_nested(self, service):
        data = {
            "contact": {
                "name": "张三",
                "phone": "13812345678",
            }
        }
        masked_data, mapping = await service.mask_dict(data, ["contact"])
        assert "张三" not in str(masked_data["contact"])

    @pytest.mark.asyncio
    async def test_mask_dict_roundtrip(self, service):
        data = {"name": "张三", "phone": "13812345678"}
        masked_data, mapping = await service.mask_dict(data, ["name", "phone"])
        restored_name = await service.unmask(masked_data["name"], mapping)
        restored_phone = await service.unmask(masked_data["phone"], mapping)
        assert restored_name == "张三"
        assert restored_phone == "13812345678"


# ── Mapping Table Security ────────────────────────────────────────────────


class TestMappingSecurity:

    @pytest.mark.asyncio
    async def test_mapping_not_in_masked_text(self, service):
        original = "张三的邮箱test@example.com"
        masked, mapping = await service.mask(original)
        for original_value in mapping.values():
            assert original_value not in masked

    @pytest.mark.asyncio
    async def test_mapping_does_not_leak_between_calls(self, service):
        _, mapping1 = await service.mask("张三的电话13812345678")
        _, mapping2 = await service.mask("李四的邮箱ls@test.com")
        assert "张三" not in mapping2.values()
        assert "李四" not in mapping1.values()

    @pytest.mark.asyncio
    async def test_duplicate_pii_single_placeholder(self, service):
        """Same PII value in one text gets one placeholder."""
        text = "张三的电话，联系张三"
        masked, mapping = await service.mask(text)
        assert "[NAME_1]" in masked
        name_placeholders = [k for k in mapping if k.startswith("[NAME_")]
        # Same name should reuse the same placeholder
        assert masked.count("[NAME_1]") == 2


# ── Concurrency ───────────────────────────────────────────────────────────


class TestConcurrency:

    @pytest.mark.asyncio
    async def test_concurrent_masking(self, service):
        texts = [
            f"用户{['张三', '李四', '王五'][i]}电话{['13800001111', '13900002222', '15000003333'][i]}"
            for i in range(3)
        ]
        results = await asyncio.gather(*[service.mask(t) for t in texts])
        for i, (masked, mapping) in enumerate(results):
            original_name = ["张三", "李四", "王五"][i]
            assert original_name not in masked
            assert original_name in mapping.values()


# ── Edge Cases ────────────────────────────────────────────────────────────


class TestEdgeCases:

    @pytest.mark.asyncio
    async def test_empty_string(self, service):
        masked, mapping = await service.mask("")
        assert masked == ""
        assert mapping == {}

    @pytest.mark.asyncio
    async def test_no_pii(self, service):
        text = "这是一段普通文字没有敏感信息"
        masked, mapping = await service.mask(text)
        assert masked == text
        assert mapping == {}

    @pytest.mark.asyncio
    async def test_only_pii(self, service):
        text = "13812345678"
        masked, mapping = await service.mask(text)
        assert "13812345678" not in masked
        assert len(mapping) >= 1

    @pytest.mark.asyncio
    async def test_placeholder_format(self, service):
        text = "张三test@example.com13812345678"
        masked, mapping = await service.mask(text)
        for key in mapping:
            assert key.startswith("[") and key.endswith("]")
            # Format: [TYPE_N]
            inner = key[1:-1]
            parts = inner.split("_")
            assert len(parts) == 2
            assert parts[0] in ("NAME", "PHONE", "EMAIL", "ID_CARD", "ADDRESS")
            assert parts[1].isdigit()
