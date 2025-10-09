from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field


class ReactionStepDescriptionRecord(BaseModel):
    """
    这个class用于规定inout记录的格式
    -input: [
                {"role":"system",
                "content":""},  # system的content是系统提示词，在初始化chain时填入当前模型的提示词
                {"role":"system",
                "content":""}   # 每个record的input text
            ]
    """
    id: str
    input: List[Dict]
    output: Dict
    predict_output: Dict  # 模型预测输出
    llm_response: str | None
    model: str | None
    status: str | None
    name: str | None
    header_name: str | None

class ReactionStepDescription(BaseModel):
    """
    Represents a single synthesis step as extracted from patent text.
    - Each record corresponds to **one and only one** synthesis step.
    - All fields are directly and literally extracted from the text; do not infer or merge.
    """

    compound_id: str = Field(
        description=(
            "Identifier for the final product of this step (e.g., 'Compound 2', 'Intermediate B'). "
            "Use the exact label from the text. If absent, set to empty string."
        )
    )
    iupac_name: str = Field(
        description=(
            "The IUPAC name of the product for this specific step, only if explicitly stated in the text. "
            "If not present, set to empty string."
        )
    )
    structure_id: str = Field(
        default="",
        description=(
            "The <mol id=...> of the final product if a corresponding structure is given for this step, "
            "and only if it is the last product-forming step in the Example/Section. Otherwise, empty string."
        ),
    )
    detail_ids: List[str] = Field(
        description=(
            "Ordered list of <text id=...> block IDs that together fully describe this step's procedure."
        )
    )
    detail: str = Field(
        description=(
            "Verbatim concatenation of all procedural text for this step, from the specified detail_ids. "
            "Includes operations, reagents, yields, conditions, and any analytical data present in those blocks."
        )
    )
    refs: Optional[List[str]] = Field(
        description=(
            "List of exact compound identifiers (e.g., 'Compound 1', 'Intermediate A') referenced in this step "
            "as precursors or reagents. If none, set to null."
        )
    )


class CompoundBaseInfo(BaseModel):
    """
    化合物基础信息模型
    """
    compound_id: str = Field(
        default="",
        description=(
            "A unique identifier assigned to a specific chemical compound in a chemical synthesis example. "
            "It uses terms like 'Intermediate xxx', 'Example xxx', 'Compound xxx', 'Preparation xxx' or 'Intermediate xxx', "
            "where 'xxx' is a short string or numerical value. If no exist, please assign an empty string value to this field."
        )
    )
    iupac_name: str = Field(
        default="",
        description=(
            "A Union of Pure and Applied Chemistry (IUPAC), a standardized way to refer to chemicals "
            "(e.g., 'water', 'sodium chloride'). If no exist, please assign an empty string value to this field."
        )
    )
    quantity: str = Field(
        default="",
        description=(
            "The amount of the substance, typically expressed in mass (grams) or volume (milliliters). "
            "If no exist, please assign an empty string value to this field."
        )
    )
    moles: str = Field(
        default="",
        description=(
            "The number of moles of the substance, expressed in mol. "
            "If no exist, please assign an empty string value to this field."
        )
    )


class Condition(BaseModel):
    """
    反应条件模型
    """
    name: str = Field(
        description="The type of condition (e.g., 'temperature', 'duration')"
    )
    value: str = Field(
        description="The value of the condition (e.g., '25°C', '10 min')"
    )


class ReactionInfo(BaseModel):
    """
    反应信息模型
    """
    action: str = Field(
        description="A description of the action performed in the synthesis, e.g., 'stir', 'heat', 'cool', 'mix'."
    )
    reactants: List[CompoundBaseInfo] = Field(
        description="A list of substances involved as reactants in the synthesis"
    )
    conditions: Optional[List[Condition]] = Field(
        default=None,
        description="A list of conditions applied during this step, each with a name and value (e.g., 'temperature: 25°C', 'duration: 10 minutes')"
    )
    reagents: Optional[List[CompoundBaseInfo]] = Field(
        default=None,
        description="A list of reagents used in the synthesis, if applicable. Include the compound_id, iupac_name, quantity, and moles."
    )
    solvents: Optional[List[CompoundBaseInfo]] = Field(
        default=None,
        description="A list of solvents used in the synthesis, if applicable. Include the compound_id, iupac_name, quantity, and moles."
    )
    products: List[CompoundBaseInfo] = Field(
        description="List of products from synthesis description in this specific step. Include the compound_id, iupac_name, quantity, and moles."
    )
    yield_: Optional[str] = Field(
        default=None,
        description="The yield of the reaction step, typically expressed as a percentage (e.g., '85%'). If not provided, use an empty string."
    )
    lcms: Optional[str] = Field(
        default=None,
        description="The LCMS (Liquid Chromatography-Mass Spectrometry) data or analysis for the reaction step (if applicable)."
    )
    nmr: Optional[str] = Field(
        default=None,
        description="The NMR (Nuclear Magnetic Resonance) data or analysis for the reaction step (if applicable)."
    )