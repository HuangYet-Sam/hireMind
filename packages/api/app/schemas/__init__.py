from pydantic import BaseModel, ConfigDict


def to_camel(snake: str) -> str:
    components = snake.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class HireMindModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
