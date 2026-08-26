"""Course-level content contracts and teacher-confirmable case blueprints."""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any


COURSE_CONTRACTS: dict[str, dict[str, Any]] = {
    "stochastic_programming": {
        "name": "随机规划",
        "family": "运筹学 / 管理科学",
        "match": ("随机规划", "随机优化", "stochastic programming"),
        "required_elements": [
            ("decision_stages", "决策阶段", "区分先验决策与随机信息揭示后的追索决策"),
            ("random_variables", "随机变量", "定义需求、价格或供给等不确定参数及取值范围"),
            ("scenarios", "情景及概率", "给出至少三个情景、发生概率和数据表"),
            ("decision_variables", "决策变量", "明确一阶段变量与二阶段变量的业务含义"),
            ("objective_function", "目标函数", "比较期望成本、收益或风险度量"),
            ("constraints", "约束条件", "写出资源、能力、平衡关系和非负等约束"),
            ("solution_comparison", "方案计算与比较", "比较随机规划、确定性方案及不同风险偏好结果"),
        ],
        "evidence_plan": ["情景—概率—参数数据表", "变量与约束说明表", "至少两种方案的结果对比", "敏感性或风险分析"],
        "roles": ["负责资源配置的决策者", "建立模型的运筹分析师", "提供概率与业务数据的需求/运营负责人"],
        "decision_task": "在随机信息尚未完全揭示时确定一阶段方案，并说明追索策略、期望目标值和风险取舍。",
        "forbidden_patterns": ["组织变革阻力", "培训是否到位", "中层与一线是否支持改革"],
    },
    "contract_law": {
        "name": "合同法",
        "family": "法学 / 民商法",
        "match": ("合同法", "合同纠纷", "合同编", "违约责任"),
        "required_elements": [
            ("jurisdiction", "法域与时间", "确认适用法域、合同订立时间和规则有效时间"),
            ("parties", "当事人与法律关系", "明确合同主体、代理关系及各自权利义务"),
            ("clauses", "具体合同条款", "逐条呈现价格、履行、验收、变更、解除和违约条款"),
            ("chronology", "履约与争议时间线", "区分已确认事实、双方主张和仍待证明事实"),
            ("legal_rules", "法律规则与来源", "列出需要适用的规则、权威来源及适用条件"),
            ("claims_defenses", "请求、抗辩与争议焦点", "分别呈现双方请求权基础、抗辩和证据"),
            ("remedies", "责任与救济", "比较继续履行、解除、损害赔偿及程序选择"),
        ],
        "evidence_plan": ["合同条款摘录", "履约时间线", "往来通知与验收记录", "双方主张—证据—规则对照表"],
        "roles": ["合同双方当事人", "双方代理人或法务", "中立的审判/仲裁角色"],
        "decision_task": "识别争议焦点，完成规则—事实—论证链，并提出有依据的责任认定与救济方案。",
        "forbidden_patterns": ["员工抵触改革", "跨部门培训", "扩大组织试点"],
    },
}


SUBJECT_FALLBACKS: dict[str, dict[str, Any]] = {
    "管理学": {
        "name": "管理与商科通用",
        "family": "管理与商科",
        "required_elements": [
            ("mechanism", "核心管理机制", "明确需要应用的理论机制，而非只写人物立场"),
            ("evidence", "管理证据", "提供指标、流程、资源、访谈或决策记录"),
            ("tradeoff", "决策变量与取舍", "说明资源、激励、治理或能力之间的取舍"),
        ],
        "evidence_plan": ["关键指标或流程证据", "利益相关者信息", "备选方案比较"],
        "roles": ["承担结果的决策者", "掌握专业证据的角色", "受决策影响的角色"],
        "decision_task": "使用课程机制解释证据，并提出可执行且能承担风险的管理决策。",
        "forbidden_patterns": [],
    },
    "法学": {
        "name": "法学通用",
        "family": "法学",
        "required_elements": [
            ("jurisdiction", "法域与时间", "明确适用法域与规则时间"),
            ("facts", "法律事实与时间线", "区分确认事实、主张和待证事实"),
            ("rules", "规则与权威来源", "给出规则来源、构成要件和适用条件"),
            ("arguments", "争点与双向论证", "呈现请求、抗辩和证据链"),
        ],
        "evidence_plan": ["事实时间线", "规则来源", "双方论证与证据"],
        "roles": ["权利义务主体", "代理或执法角色", "裁判或审查角色"],
        "decision_task": "围绕争点完成规则—事实—结论的双向论证。",
        "forbidden_patterns": ["泛化组织变革故事"],
    },
    "经济学": {
        "name": "经济与金融分析",
        "family": "经济学 / 金融学",
        "required_elements": [
            ("economic_agents", "经济主体与激励", "明确主体、目标、信息与行为假设"),
            ("variables_data", "变量、口径与数据", "给出变量定义、单位、样本或参数来源"),
            ("mechanism_model", "经济机制或模型", "呈现因果机制、均衡关系或计量识别思路"),
            ("counterfactual", "基准与反事实", "设置可以比较的政策、市场或投资情景"),
            ("welfare_risk", "效果、分配与风险", "比较效率、分配影响、稳健性和外部性"),
        ],
        "evidence_plan": ["变量与数据口径表", "基准情景", "机制或模型图", "反事实结果与稳健性分析"],
        "roles": ["经济决策主体", "掌握数据与模型的分析者", "受政策或市场变化影响的主体"],
        "decision_task": "使用明确的经济机制和数据比较基准与反事实，并说明效率、分配和风险后果。",
        "forbidden_patterns": ["只描述态度而没有变量与机制"],
    },
    "计算机科学": {
        "name": "计算机与信息系统",
        "family": "计算机科学 / 信息系统",
        "required_elements": [
            ("system_boundary", "系统边界与使用场景", "明确用户、输入输出、依赖和运行环境"),
            ("technical_artifact", "技术对象", "提供架构、算法、数据结构、接口或代码片段"),
            ("requirements", "功能与非功能需求", "给出性能、可靠性、安全、可维护性等指标"),
            ("failure_evidence", "故障证据与复现", "提供日志、测试、指标或攻击路径等可分析证据"),
            ("tradeoff", "技术方案与权衡", "比较至少两种方案的复杂度、成本、风险和适用条件"),
        ],
        "evidence_plan": ["系统架构或流程图", "输入输出样例", "日志/测试/性能数据", "方案对比表"],
        "roles": ["需求或产品负责人", "开发/架构/数据工程角色", "测试、安全、运维或最终用户"],
        "decision_task": "基于可复现技术证据诊断问题，比较方案并提交可验证的实现或架构决策。",
        "forbidden_patterns": ["用沟通问题代替技术证据", "没有输入输出或测试结果"],
    },
    "工程技术": {
        "name": "工程设计与系统分析",
        "family": "工程技术",
        "required_elements": [
            ("engineering_object", "工程对象与工况", "明确系统边界、运行环境、载荷或工况"),
            ("design_parameters", "设计参数与单位", "给出关键参数、单位、允许范围和数据来源"),
            ("constraints_standards", "约束与标准", "说明安全、资源、法规、接口或制造约束"),
            ("analysis_evidence", "分析、试验与证据", "提供计算、试验、故障或监测结果"),
            ("design_tradeoff", "方案与工程权衡", "比较性能、安全、成本、进度和可维护性"),
        ],
        "evidence_plan": ["工程参数表", "系统/部件关系图", "试验或监测数据", "设计方案权衡矩阵"],
        "roles": ["总体或设计负责人", "专业工程师", "试验、安全、制造或运行角色"],
        "decision_task": "依据参数、约束和试验数据完成工程判断，并说明方案的安全裕度与失效风险。",
        "forbidden_patterns": ["只有项目沟通而没有工程参数", "没有试验或计算证据"],
    },
    "教育学": {
        "name": "教育与学习科学",
        "family": "教育学",
        "required_elements": [
            ("learners_context", "学习者与教学情境", "明确学习者特征、前置能力和情境约束"),
            ("learning_evidence", "学习证据", "提供作品、测评、观察、访谈或过程数据"),
            ("learning_mechanism", "学习机制与理论", "用课程理论解释困难形成机制"),
            ("intervention", "教学干预", "设计目标、活动、支架、资源和实施条件"),
            ("evaluation", "评价与改进", "定义效果证据、比较基准和迭代方法"),
        ],
        "evidence_plan": ["学习者画像", "前测/作品/课堂观察", "干预流程", "评价量规与结果"],
        "roles": ["学习者", "教师或课程设计者", "教研、家长或管理支持角色"],
        "decision_task": "依据学习证据诊断困难，设计理论一致的干预并说明如何评价和迭代。",
        "forbidden_patterns": ["只评价教师态度", "没有学习产出证据"],
    },
    "医学与健康": {
        "name": "医学与健康决策",
        "family": "医学 / 公共健康",
        "required_elements": [
            ("clinical_context", "人群或临床情境", "明确对象、时间过程、环境和风险边界"),
            ("findings", "观察与检查证据", "区分症状、体征、检查、暴露和缺失信息"),
            ("differential", "竞争性解释", "提出并比较多个合理诊断或机制假设"),
            ("guideline_evidence", "指南或证据来源", "标注指南、共识或研究证据及适用条件"),
            ("decision_safety", "干预、伦理与安全", "比较获益、风险、知情同意和随访监测"),
        ],
        "evidence_plan": ["时间线与主诉", "检查结果表", "鉴别诊断矩阵", "指南证据和安全监测"],
        "roles": ["患者或目标人群", "临床/公共卫生专业人员", "检验、护理、伦理或管理角色"],
        "decision_task": "在证据不完整条件下完成鉴别与风险分层，并提出安全、可复核的下一步方案。",
        "forbidden_patterns": ["输出无来源的确定性诊断", "忽略伦理和安全边界"],
    },
}


def _text(payload: dict[str, Any]) -> str:
    objectives = payload.get("learning_objectives") or []
    return " ".join(str(value) for value in [payload.get("title"), payload.get("course_name"), payload.get("subject"), *objectives]).lower()


def select_course_contract(payload: dict[str, Any]) -> tuple[str, dict[str, Any], bool]:
    context = _text(payload)
    for contract_id, contract in COURSE_CONTRACTS.items():
        if any(keyword.lower() in context for keyword in contract["match"]):
            return contract_id, deepcopy(contract), True
    subject = str(payload.get("subject") or "管理学")
    subject_aliases = {"经济与金融": "经济学", "计算机与信息": "计算机科学", "教育": "教育学", "医学": "医学与健康", "工程": "工程技术"}
    fallback_key = subject_aliases.get(subject, subject)
    fallback = deepcopy(SUBJECT_FALLBACKS.get(fallback_key) or SUBJECT_FALLBACKS["管理学"])
    return f"subject:{subject}", fallback, False


def blueprint_signature(payload: dict[str, Any]) -> str:
    objectives = "；".join(str(item).strip() for item in payload.get("learning_objectives") or [])
    brief = payload.get("objective_brief") or {}
    brief_text = "；".join(str(brief.get(key) or "").strip() for key in ("learning_challenge", "desired_performance", "required_concepts", "assessment_evidence"))
    raw = "|".join([
        *(str(payload.get(key) or "").strip() for key in ("title", "subject", "course_name", "case_type", "difficulty", "target_audience")),
        objectives, brief_text,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_case_blueprint(payload: dict[str, Any]) -> dict[str, Any]:
    contract_id, contract, exact = select_course_contract(payload)
    title = str(payload.get("title") or "教学案例").strip()
    course = str(payload.get("course_name") or payload.get("subject") or "课程").strip()
    required = [
        {"key": key, "label": label, "planned_use": use, "required": True}
        for key, label, use in contract["required_elements"]
    ]
    missing = [] if exact else [f"当前仅匹配到“{contract['name']}”通用规则，请确认必用概念和证据类型。"]
    brief = payload.get("objective_brief") or {}
    required_concepts = str(brief.get("required_concepts") or "").strip()
    if required_concepts:
        required.append({"key": "teacher_concepts", "label": "教师指定知识", "planned_use": required_concepts, "required": True})
    return {
        "signature": blueprint_signature(payload),
        "contract_id": contract_id,
        "contract_name": contract["name"],
        "course_family": contract["family"],
        "exact_match": exact,
        "case_core": f"围绕“{title}”设计一项必须使用《{course}》专业知识才能完成的判断任务。",
        "required_elements": required,
        "evidence_plan": list(contract["evidence_plan"]),
        "roles": list(contract["roles"]),
        "decision_task": contract["decision_task"],
        "fact_boundary": "未提供权威来源的机构、人物、数据和争议过程均标记为教学虚构；专业规则需注明法域、时间或出处。",
        "forbidden_patterns": list(contract.get("forbidden_patterns") or []),
        "missing_information": missing,
        "authenticity_score": 92 if exact else 68,
        "approved": False,
    }


def validate_approved_blueprint(payload: dict[str, Any], blueprint: dict[str, Any] | None) -> list[str]:
    if not blueprint:
        return ["请先生成并确认案例蓝图"]
    issues: list[str] = []
    if blueprint.get("signature") != blueprint_signature(payload):
        issues.append("课程情境已发生变化，请重新生成案例蓝图")
    expected_id, expected_contract, expected_exact = select_course_contract(payload)
    if blueprint.get("contract_id") != expected_id or bool(blueprint.get("exact_match")) != expected_exact:
        issues.append("案例蓝图与当前课程内容契约不一致，请重新生成")
    if not blueprint.get("approved"):
        issues.append("案例蓝图尚未由教师确认")
    required = blueprint.get("required_elements") or []
    if not required or any(not str(item.get("planned_use") or "").strip() for item in required if isinstance(item, dict) and item.get("required")):
        issues.append("案例蓝图中的必备学科要素尚未填写完整")
    submitted_keys = {str(item.get("key")) for item in required if isinstance(item, dict)}
    expected_keys = {str(item[0]) for item in expected_contract.get("required_elements") or []}
    missing_keys = expected_keys - submitted_keys
    if missing_keys:
        issues.append("案例蓝图不得删除必备学科要素：" + "、".join(sorted(missing_keys)))
    if not str(blueprint.get("decision_task") or "").strip():
        issues.append("案例蓝图缺少最终课堂任务")
    return issues


def normalized_shingles(text: str, width: int = 5) -> set[str]:
    normalized = re.sub(r"\s+|[，。！？；：、“”‘’（）()《》]", "", str(text or ""))
    return {normalized[index : index + width] for index in range(max(0, len(normalized) - width + 1))}


def text_similarity(left: str, right: str) -> float:
    a, b = normalized_shingles(left), normalized_shingles(right)
    return len(a & b) / max(len(a | b), 1)
