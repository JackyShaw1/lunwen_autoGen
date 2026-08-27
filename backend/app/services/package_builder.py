"""任务参数驱动的教学案例四件套构建（Mock / LLM 后处理共用）"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from app.models import CaseTask
from app.services.rubric_service import score_package
from app.services.course_blueprint_service import select_course_contract
from app.services.grounded_case_service import find_grounded_profile, generation_preflight_error
from app.services.material_service import get_official_material, material_context_signature, recommended_materials
from app.services.video_service import recommended_videos


RESOURCE_TARGET_COUNT = 10


def count_case_body_chars(package: dict[str, Any]) -> int:
    """统计案例正文可见字符：背景 + 叙事 + 决策点，不计空白。"""
    body = package.get("body") or {}
    text = "".join(str(body.get(key) or "") for key in ("background", "narrative", "decision_point"))
    return len(re.sub(r"\s+", "", text))


def update_body_length_meta(package: dict[str, Any], target_words: int) -> int:
    actual = count_case_body_chars(package)
    meta = package.setdefault("meta", {})
    meta["target_words"] = target_words
    meta["actual_words"] = actual
    meta["word_count_scope"] = "背景、案例叙述与决策点的可见字符（不计空白）"
    return actual


def build_teaching_flow(class_hours: int) -> str:
    """Build a complete teaching schedule that always fits the configured 45-minute periods."""
    hours = max(int(class_hours or 1), 1)
    total = hours * 45
    phases = [
        ("情境导入与案例阅读", 18),
        ("小组分析与方案形成", 30),
        ("小组汇报与交叉质询", 27),
        ("教师点评与理论回扣", 16),
    ]
    minutes: list[int] = []
    allocated = 0
    for _, weight in phases[:-1]:
        value = max(round(total * weight / 100), 1)
        minutes.append(value)
        allocated += value
    minutes.append(max(total - allocated, 1))
    steps = "→".join(f"{label}({minute}min)" for (label, _), minute in zip(phases, minutes))
    # Do not repeat the numeric total with a “分钟” suffix here: the release validator
    # intentionally sums every explicit minute value in the flow.
    return f"建议 {hours} 课时：{steps}"


def fit_teaching_flow_to_class_hours(package: dict[str, Any], class_hours: int) -> bool:
    """Replace absent or overflowing model schedules with a deterministic valid schedule."""
    guide = package.setdefault("instructor_guide", {})
    flow = str(guide.get("teaching_flow") or "")
    minutes = sum(int(value) for value in re.findall(r"(\d+)\s*(?:min|分钟)", flow, flags=re.I))
    available = max(int(class_hours or 1), 1) * 45
    if not flow.strip() or minutes == 0 or minutes > available:
        guide["teaching_flow"] = build_teaching_flow(class_hours)
        return True
    return False


def normalize_case_package(package: dict[str, Any]) -> dict[str, Any]:
    """Remove internal annotations from all student-facing body fields and preserve them once."""
    body = package.setdefault("body", {})
    existing_context = package.get("domain_context") or {}
    existing_notes = (
        existing_context.get("notes", "")
        if isinstance(existing_context, dict)
        else str(existing_context)
    )
    candidates = [existing_notes]
    changed = False
    for key in ("background", "narrative", "decision_point"):
        text = str(body.get(key) or "")
        if "【学科注释】" not in text:
            continue
        parts = re.split(r"\s*【学科注释】\s*", text)
        body[key] = parts[0].strip()
        candidates.extend(parts[1:])
        changed = True

    unique_notes: list[str] = []
    seen: set[str] = set()
    for note in candidates:
        cleaned = str(note or "").strip()
        fingerprint = re.sub(r"\s+", "", cleaned)
        if cleaned and fingerprint not in seen:
            seen.add(fingerprint)
            unique_notes.append(cleaned)
    if unique_notes:
        package["domain_context"] = {"notes": "\n".join(unique_notes)}
    if not changed:
        return package
    target_words = int((package.get("meta") or {}).get("target_words") or 0)
    if target_words:
        update_body_length_meta(package, target_words)
    return package


def _truncate_visible_chars(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    count = 0
    end = len(text)
    for index, char in enumerate(text):
        if not char.isspace():
            count += 1
        if count >= limit:
            end = index + 1
            break
    clipped = text[:end].rstrip("，；：、 ")
    sentence_end = max(clipped.rfind("。"), clipped.rfind("！"), clipped.rfind("？"))
    if sentence_end >= int(len(clipped) * 0.88):
        clipped = clipped[: sentence_end + 1]
    elif clipped and clipped[-1] not in "。！？":
        clipped += "。"
    return clipped


def ensure_mock_body_length(package: dict[str, Any], task: CaseTask) -> int:
    """为 Mock 模式生成接近目标篇幅的完整叙事，避免短模板冒充成品。"""
    body = package.setdefault("body", {})
    title = task.title
    subject = task.subject
    course = task.course_name
    audience = task.target_audience
    special = (task.config or {}).get("special_requirements") or ""

    segments = [
        f"三个月前，围绕“{title}”的专项计划被正式列入年度重点任务。管理层希望借此回应外部环境变化，也希望在有限时间内形成能够被复制的做法。项目启动时，几乎所有人都认可改变的必要性，但对于先做什么、由谁承担风险以及用什么标准判断成效，各部门并没有形成真正一致的答案。",
        f"陈启明作为项目负责人，在首次启动会上展示了清晰的里程碑：第一个月完成准备，第二个月进入试运行，第三个月提交阶段成果。他强调，组织已经错过过一次窗口期，如果再次延后，不仅预算可能被收回，团队也会失去高层支持。会议记录显示，多数参会者当场表示同意，但会后提交的风险清单却不断增加。",
        "林晓雯负责跨部门协调。她很快发现，表面上的共识掩盖了完全不同的理解：决策层把任务视为战略落地，职能部门把它视为流程调整，一线员工则把它理解为额外工作。三方使用相同的项目名称，却在讨论不同的问题。她尝试建立共同的问题清单，但每个部门都更关心自身指标是否会受到影响。",
        "赵磊代表一线团队参加第二次协调会。他没有否定项目方向，而是列出最近四周的排班、返工和客户反馈数据，说明团队已接近负荷上限。如果在培训和岗位安排尚未完成时直接切换流程，短期指标也许会改善，但错误成本会被转移给最靠近客户的人。他的发言让会议气氛第一次变得紧张。",
        "陈启明认为这些问题可以在推进过程中逐步解决。他担心过度讨论会让组织重新回到观望状态，因此要求各部门先执行统一方案，再根据数据调整。林晓雯则提出，执行不是简单服从；如果关键参与者不知道改变与自身工作的关系，再完整的计划也可能只停留在汇报材料中。双方的分歧从进度安排逐渐转向对“有效执行”的不同理解。",
        f"为了获得更客观的判断，项目组从{subject}视角梳理了现有证据。数据显示，试点环节的处理速度有所提高，但跨部门等待时间并未下降；部分员工掌握了新方法，另一些人仍依赖旧流程；管理层看到的是整体趋势，一线看到的却是每天发生的具体摩擦。不同粒度的数据支持了不同结论，也让简单的是非判断变得困难。",
        "随后的一次小范围试运行暴露了新的矛盾。技术与流程本身能够运行，但岗位责任边界变得模糊：出现问题时，原部门认为应由项目组处理，项目组则认为业务部门应对结果负责。两次客户投诉虽然得到及时解决，却没有任何团队愿意在复盘会上承认这是制度设计问题。每个人都在保护自己的可控范围。",
        "林晓雯分别与关键成员进行访谈。年轻员工普遍愿意尝试，但担心犯错会影响考核；资深员工并非抗拒变化，而是认为既有经验被轻易否定；中层管理者最矛盾，他们既要向上证明执行力度，又要承担团队波动带来的现实后果。这些信息没有直接给出答案，却说明所谓“阻力”并不是单一态度问题。",
        f"在《{course}》所关注的组织情境中，正式权力、专业判断和非正式影响同时发挥作用。陈启明拥有资源配置权，赵磊掌握一线经验，林晓雯则连接了原本彼此隔离的信息。任何一方单独推进都可能获得局部成功，却难以形成稳定结果。问题的核心逐渐从选择某个工具，转变为如何建立共同承担结果的机制。",
        "第三次项目会议前，高层发来通知，要求提前两周展示成果。陈启明据此主张扩大试点范围，用更明显的数据证明项目价值。赵磊反对在问题尚未闭环时扩大规模，认为这会把局部风险快速复制。林晓雯提出折中方案：保持总体目标不变，但重新划分试点边界，并用一周时间完成关键岗位训练和责任确认。",
        "这一方案同样存在代价。缩小试点可能被解读为项目退缩；增加训练会挤占正常工作；重新讨论责任边界又可能引发部门之间的资源争夺。更重要的是，团队需要决定哪些指标代表真正进展：是按期上线、短期效率、员工接受度，还是客户体验。不同指标背后对应着不同利益，也会导向不同的行动。",
        "会前一天，赵磊提交了一份联合签名的建议书。建议书没有要求暂停项目，而是要求公开试点数据、明确异常处理权限，并允许一线成员参与每周复盘。陈启明意识到，如果接受这些要求，原计划必须调整；如果拒绝，项目仍可按时推进，但一线可能只做最低限度的配合。形式上的速度与长期的执行质量形成直接冲突。",
        "与此同时，财务部门提醒剩余预算必须在本季度内使用，人力部门则表示集中培训最快也要两周。客户侧没有给出明确期限，却开始询问组织能否提供更稳定的交付承诺。三个时间尺度相互挤压，使得任何方案都无法同时满足所有条件。决策者必须明确，哪些风险可以接受，哪些能力必须在扩大行动前补齐。",
        f"{('教师特别要求也被纳入判断：' + special + '。') if special else ''} 对面向{audience}的课堂讨论而言，这一情境并不存在唯一正确答案。学生需要区分事实、推测与立场，识别各方掌握的信息及其盲区，并说明自己选择的方案如何兼顾短期成果与长期能力建设。",
        "最终协调会开始时，陈启明没有立即公布决定，而是把三个方案写在白板上：维持原计划并扩大试点；暂缓扩围、集中补齐训练与责任机制；重新设定阶段目标，以较慢速度换取更多参与。会议室里的每个人都知道，选择任何一项都意味着放弃另一些价值，而决定必须在当天作出。",
    ]

    evidence_topics = [
        ("绩效考核", "现有指标奖励短期速度，却没有记录跨部门协作成本", "调整指标可能降低短期可比性"),
        ("信息透明", "关键数据分散在不同系统，解释权掌握在少数岗位手中", "完全公开也可能引发防御行为"),
        ("能力准备", "培训完成率与实际独立操作能力并不相同", "等待所有人准备完毕会错过窗口"),
        ("客户影响", "内部效率提升尚未稳定转化为客户体验", "过早承诺可能放大信誉风险"),
        ("中层角色", "中层既是执行者也是意义解释者", "授权过少难以协调，授权过多又可能失控"),
        ("试点边界", "不同部门选择了对自己最有利的样本", "扩大样本会提高真实性也会增加失败概率"),
        ("复盘机制", "问题被及时处理却没有沉淀为共同规则", "高频复盘会进一步占用业务时间"),
        ("资源配置", "预算、人员与时间分别由不同负责人控制", "集中资源意味着其他任务必须让位"),
        ("心理安全", "员工愿意私下表达担忧，却很少在正式会议提出异议", "鼓励异议可能延长决策过程"),
        ("治理责任", "项目成功由集体分享，失败责任却可能落到单一部门", "共同负责需要同步重构授权关系"),
    ]

    narrative_parts = list(segments)
    body["narrative"] = "\n\n".join(narrative_parts)
    min_chars = int(task.target_words * 0.98)
    index = 0
    while count_case_body_chars(package) < min_chars:
        topic, evidence, tradeoff = evidence_topics[index % len(evidence_topics)]
        narrative_parts.append(
            f"在第{index + 1}轮补充讨论中，团队把“{topic}”单独列为判断维度。现有材料表明，{evidence}；但如果立即修正，{tradeoff}。陈启明要求用结果证明必要性，林晓雯关注不同部门能否形成共同规则，赵磊则追问风险最终由谁承担。这一轮讨论没有消除分歧，却让各方必须公开自己的判断标准。"
        )
        body["narrative"] = "\n\n".join(narrative_parts)
        index += 1

    max_chars = int(task.target_words * 1.05)
    actual = count_case_body_chars(package)
    if actual > max_chars:
        other_chars = count_case_body_chars({"body": {"background": body.get("background"), "decision_point": body.get("decision_point")}})
        body["narrative"] = _truncate_visible_chars(body["narrative"], max(task.target_words - other_chars, 500))
    actual = update_body_length_meta(package, task.target_words)
    score_package(package)
    return actual


def _objectives(task: CaseTask) -> list[dict[str, Any]]:
    objs = task.learning_objectives or []
    if not objs:
        objs = [f"理解并分析「{task.title}」中的关键决策"]
    return [
        {
            "id": f"LO{i + 1}",
            "level": "分析" if i == 0 else ("评价" if i == 1 else "应用"),
            "description": obj,
            "assessment_hint": "课堂讨论与汇报",
        }
        for i, obj in enumerate(objs)
    ]


def _build_grounded_package(task: CaseTask, profile: dict[str, Any]) -> dict[str, Any]:
    """Assemble an audited factual package without generic fictional filler."""
    title = task.title
    subject = task.subject
    course = task.course_name
    learning_objectives = deepcopy(profile.get("learning_objectives") or [])
    sources = deepcopy(profile.get("evidence_sources") or [])
    assets = [
        dict(asset)
        for asset_id in profile.get("visual_asset_ids") or []
        if (asset := get_official_material(str(asset_id))) is not None
    ]
    material_query = f"{title} {subject} {course} {task.case_type}"
    videos = recommended_videos(material_query, limit=RESOURCE_TARGET_COUNT)
    package: dict[str, Any] = {
        "meta": {
            "title": title,
            "subject": subject,
            "course": course,
            "difficulty": task.difficulty,
            "case_type": task.case_type,
            "target_audience": task.target_audience,
            "target_words": task.target_words,
            "content_mode": "source_grounded",
            "source_policy": "仅陈述来源支持的事实；课堂角色不冒充真实历史人物；推断必须明确标注",
            "fictional_disclaimer": "本案例依据公开可核验资料编写；课堂模拟角色仅用于方法训练，不代表未公开历史事实。",
        },
        "teacher_requirements": {
            "original": list(task.learning_objectives or []),
            **deepcopy(profile.get("teacher_brief") or {}),
            "special_requirements": str((task.config or {}).get("special_requirements") or ""),
        },
        "learning_objectives": learning_objectives,
        "body": {
            **deepcopy(profile.get("body") or {}),
            "characters": deepcopy(profile.get("characters") or []),
        },
        "discussion_questions": deepcopy(profile.get("discussion_questions") or []),
        "instructor_guide": {
            "teaching_flow": build_teaching_flow(int((task.config or {}).get("class_hours") or 2)),
            **deepcopy(profile.get("instructor_guide") or {}),
            "extension_reading": [f"[{source['id']}] {source['title']}｜{source['source_page_url']}" for source in sources],
        },
        "alignment_matrix": [
            {
                "objective_id": objective["id"],
                "case_section": "真实案例证据链与课堂迁移任务",
                "activity": "证据卡研讨、闭环建模与角色模拟",
                "assessment": objective.get("assessment_hint") or "课堂汇报",
            }
            for objective in learning_objectives
        ],
        "evidence_sources": sources,
        "video_resources": videos,
        "resource_targets": {
            "evidence_sources": RESOURCE_TARGET_COUNT,
            "official_visuals": RESOURCE_TARGET_COUNT,
            "recommended_visuals": RESOURCE_TARGET_COUNT,
            "videos": RESOURCE_TARGET_COUNT,
            "policy": "优先官方或高可信来源；数量不足时留空并提示，不以无关或不可核验内容凑数",
        },
        "course_ideology": deepcopy(profile.get("course_ideology") or {}),
        "visual_assets": assets,
        "material_research": {
            "context_signature": material_context_signature(title, subject, course, task.case_type),
            "query": material_query,
            "strategy": "curated_source_grounded_profile",
            "matched_count": len(assets),
            "profile_id": profile.get("id"),
        },
        "quality": {},
    }
    update_body_length_meta(package, task.target_words)
    score_package(package)
    return package


def _apply_discipline_contract(package: dict[str, Any], task: CaseTask, blueprint: dict[str, Any]) -> None:
    """Replace the generic fallback with course-native entities, evidence and decisions."""
    contract_id = str(blueprint.get("contract_id") or "")
    body = package.setdefault("body", {})
    artifacts: dict[str, Any]
    if contract_id == "stochastic_programming":
        body["characters"] = [
            {"name": "周岚", "role": "供应链计划负责人", "stance": "要求在订货截止前确定一阶段采购量"},
            {"name": "顾言", "role": "运筹分析师", "stance": "主张使用两阶段随机规划并保留追索决策"},
            {"name": "许峰", "role": "运营负责人", "stance": "担心模型平均结果掩盖高需求情景下的缺货风险"},
        ]
        body["background"] = (
            "某医疗耗材配送中心需要在季度合同锁价日前确定基础采购量。需求在采购决定后才逐步显现，"
            "而加急采购价格更高、库存剩余会产生处置成本。过去使用平均需求制定计划，在需求波动较大时频繁出现缺货或积压。"
            "本案例中的机构和数据均为教学虚构，重点训练两阶段随机规划建模与风险解释。"
        )
        segments = [
            "周岚要求团队在周五前提交采购方案。顾言把决策过程拆成两个阶段：一阶段变量x表示在需求揭示前按合同价采购的数量；二阶段变量y_s与z_s分别表示情景s发生后的加急采购量和剩余处置量。这个划分意味着课堂讨论不能只比较人物态度，而要解释哪些决策能够等待信息、哪些不能。",
            "需求被整理为三个离散情景：低需求800箱，概率0.25；基准需求1000箱，概率0.50；高需求1250箱，概率0.25。基础采购单价为每箱80元，加急采购为每箱118元，剩余处置只能回收每箱35元。仓储能力上限为1150箱，但高需求情景允许通过加急直送满足部分需求。",
            "顾言给出的平衡约束为x+y_s-z_s=d_s，其中d_s是情景需求；同时0≤x≤1150，y_s≥0，z_s≥0。目标函数不是追求某个情景的最低成本，而是最小化80x加上各情景概率加权后的追索成本，即Σp_s(118y_s-35z_s)。模型把随机变量、情景概率、决策变量和约束放进同一个可检验结构。",
            "财务部门提出确定性替代方案：直接把期望需求1000箱代入模型并采购1000箱。该方案在基准情景下表现良好，却没有说明高需求时的加急成本和低需求时的处置损失。许峰要求同时报告期望成本、最坏情景成本和缺货服务风险，避免只用一个平均数掩盖尾部后果。",
            "分析师分别计算采购900、1000和1100箱的情景成本。采购900箱保留了库存灵活性，但高需求时需要加急350箱；采购1100箱降低了高需求追索成本，却会在低需求时处置300箱；采购1000箱位于两者之间。学生需要依据概率加权结果复核，而不能把中间方案直接视为最优。",
            "新信息随后改变了模型边界。供应商提出，如果基础采购超过1050箱，超出部分可享受每箱76元的阶梯价格；但仓储部门表示超过1080箱将触发额外固定租仓费用。阶梯价格使目标函数出现分段结构，固定费用又可能需要引入0—1变量，原来的线性模型必须作出解释性调整。",
            "许峰进一步质疑三个情景的概率来自过去两年数据，而今年新增客户可能使高需求概率上升。顾言因此设计概率敏感性分析：将高需求概率从0.25逐步提高，同时保持概率和为1，观察最优x何时发生变化。概率不是装饰性数据，而是影响一阶段决策的核心输入。",
            "周岚关注的是可执行性。即使某个方案期望成本最低，如果高需求时加急供应能力上限只有180箱，平衡约束可能无法满足。团队加入y_s≤180，并讨论是否允许缺货变量u_s及其单位惩罚成本。惩罚成本如何设定，实际对应服务水平、患者影响和合同责任的价值判断。",
            "会议形成三套待选模型：只优化期望成本的风险中性模型；限制最坏情景成本的稳健方案；在目标中加入条件风险价值的风险厌恶方案。三者使用相同基础数据，却会因风险偏好不同给出不同采购量。模型选择本身也是决策的一部分。",
            "在提交前，顾言要求每个方案同时展示变量定义、目标函数、约束、情景结果和业务解释。若计算结果无法回到库存、加急采购和服务风险，就不能作为课堂中的完整随机规划方案。团队必须决定使用哪一种模型，并说明它愿意承担哪类误差。",
        ]
        body["decision_point"] = (
            "请建立并说明两阶段随机规划模型，计算或比较不同一阶段采购量在三个情景下的结果；随后在风险中性、"
            "最坏情景约束和风险厌恶方案中作出选择。答案必须明确随机变量、情景概率、决策变量、目标函数、约束条件、"
            "追索策略及敏感性分析，并说明为什么不能直接用期望需求替代随机模型。"
        )
        artifacts = {
            "scenario_table": [
                {"scenario": "低需求", "probability": 0.25, "demand": 800},
                {"scenario": "基准需求", "probability": 0.50, "demand": 1000},
                {"scenario": "高需求", "probability": 0.25, "demand": 1250},
            ],
            "variables": ["x：一阶段基础采购量", "y_s：情景s下加急采购量", "z_s：情景s下剩余处置量"],
            "objective_function": "min 80x + Σ p_s(118y_s - 35z_s)",
            "constraints": ["x + y_s - z_s = d_s", "0 ≤ x ≤ 1150", "0 ≤ y_s ≤ 180", "z_s ≥ 0"],
        }
        evidence_topics = [
            ("概率误设", "比较高需求概率变化对最优采购量的影响"),
            ("追索能力", "检验加急供应上限是否使某些方案不可行"),
            ("风险偏好", "比较期望值、最坏情景与条件风险价值的决策差异"),
            ("模型解释", "把数学结果还原为库存、服务水平和成本后果"),
        ]
        package["discussion_questions"] = [
            {"level": "理解", "question": "哪些变量属于一阶段决策，哪些属于情景揭示后的追索决策？", "teaching_intent": "识别两阶段结构"},
            {"level": "应用", "question": "根据情景表写出目标函数与平衡约束，并解释每一项业务含义。", "teaching_intent": "完成模型表达"},
            {"level": "分析", "question": "为什么用期望需求替代随机需求可能产生错误决策？", "teaching_intent": "比较确定性与随机模型"},
            {"level": "评价", "question": "风险中性与风险厌恶方案分别适合什么管理偏好？", "teaching_intent": "评价风险取舍"},
            {"level": "创造", "question": "若新增供应中断情景，你将如何修改变量、概率和约束？", "teaching_intent": "迁移建模"},
        ]
    elif contract_id == "contract_law":
        body["characters"] = [
            {"name": "甲辰设备公司", "role": "设备出卖人", "stance": "认为买方迟延验收并应支付尾款"},
            {"name": "海岳食品公司", "role": "设备买受人", "stance": "认为设备未达到约定产能并要求解除合同"},
            {"name": "仲裁庭", "role": "中立审理者", "stance": "要求双方分别证明条款含义、履约事实与损失"},
        ]
        body["background"] = (
            "本案例为中国大陆法教学场景，合同、主体和数据均为虚构。2026年3月，甲辰设备公司与海岳食品公司签订自动包装线买卖合同。"
            "案例不预设裁判结论，教师应结合授课时有效的法律文本确认规则来源，学生需区分合同条款、已确认事实、双方主张与待证事实。"
        )
        segments = [
            "合同第4条约定设备总价480万元，签约后支付30%，到货后支付40%，连续72小时验收合格后支付尾款30%。第7条约定额定产能为每小时2400件，在合同所列原料规格和环境条件下测试。第9条约定买方应在安装完成后五日内组织验收，无正当理由逾期视为完成初步验收。",
            "第11条规定，一方严重违约导致合同目的不能实现时，守约方可书面催告并在十日整改期届满后解除合同。第12条约定迟延交付违约金按合同总价每日万分之五计算，但没有明确性能不达标时损失如何计算。合同还约定争议提交约定仲裁委员会处理。",
            "5月8日设备运抵，双方签署到货清单。安装记录显示卖方于5月18日完成机械安装，但控制系统仍有两个报警项。卖方认为报警不影响生产，买方则在工作群中表示必须消除报警后才能开始72小时测试。双方没有对“安装完成”的含义另行签署书面文件。",
            "5月23日第一次测试使用了买方临时采购的薄膜材料，设备平均产能达到每小时2050件并三次停机。卖方主张薄膜厚度不符合合同附件规定，测试结果不能证明设备缺陷；买方则提交采购记录，认为卖方技术人员此前口头同意使用该批材料。口头同意是否存在及其权限成为待证事实。",
            "买方于5月25日发出《整改通知》，要求七日内达到每小时2400件，否则解除合同并索赔停产损失。卖方次日回复愿意调试，但要求先按附件规格准备材料并延长测试周期。双方对于通知是否构成第11条约定的催告、整改期应按合同十日还是通知七日计算产生争议。",
            "6月2日第二次测试达到每小时2360件，连续运行六小时后因传感器故障停机。卖方认为产能误差处于行业允许范围，且愿意免费更换传感器；买方认为合同没有约定误差区间，2360件仍低于明示指标，连续72小时条件也未满足。合同文义、交易目的和履行补救可能支持不同解释。",
            "6月5日买方向卖方发送解除通知，并拒付剩余尾款。卖方随后停用远程维护账号，主张买方未依约完成五日验收且先行拒付构成违约。买方认为尾款支付条件尚未成就，停用维护又加重设备无法使用的后果。双方的履行顺序和抗辩关系需要逐项分析。",
            "买方主张因设备未投产造成订单转包差价86万元，并提交与第三方的加工合同；卖方质疑该合同订立时间和损失可预见性，同时主张已支出的安装、差旅和零部件费用。损失是否真实、与违约是否存在因果关系、是否采取合理减损措施，均不能只凭一方陈述确认。",
            "仲裁庭将材料分为四类：无争议的合同文本和付款记录；双方签字但解释不同的安装与测试记录；仅由单方形成的通知、聊天截图和损失清单；仍需鉴定的设备性能问题。分类的目的，是防止把当事人主张直接写成已经查明的事实。",
            "双方分别提出请求。买方要求确认解除有效、返还已付款并赔偿转包损失；卖方要求支付尾款、违约金并确认买方解除无效。学生必须为每项请求寻找规则基础、构成要件、支持证据和可能抗辩，不能只凭公平感选择一方。",
        ]
        body["decision_point"] = (
            "请以授课时有效且经教师确认的合同法律规则为依据，识别本案关于验收条件、履行顺序、催告与解除、"
            "违约责任及损失证明的争议焦点。分别为买卖双方构建“请求—规则—事实—证据—抗辩”论证链，"
            "再提出继续履行、修理重作、解除合同或损害赔偿的处理方案，并标明仍需查明的事实。"
        )
        artifacts = {
            "jurisdiction": "中国大陆法教学场景；具体规则以教师确认的有效法律文本为准",
            "clauses": ["第4条：分期付款与尾款条件", "第7条：产能及测试条件", "第9条：验收期限", "第11条：催告与解除", "第12条：违约责任"],
            "chronology": ["3月签约", "5月8日到货", "5月18日安装记录", "5月23日首次测试", "5月25日整改通知", "6月2日再次测试", "6月5日解除通知"],
            "legal_issues": ["验收条件是否成就", "解除权是否成立", "双方履行抗辩", "损失与因果关系", "救济方式"],
        }
        evidence_topics = [
            ("条款解释", "比较合同文义、交易目的和履行行为对产能条款的影响"),
            ("事实证明", "区分双方认可事实、单方主张和需要鉴定的事项"),
            ("规则适用", "按构成要件逐项连接催告、解除和违约责任证据"),
            ("救济选择", "比较继续履行、修理、解除与损害赔偿的条件和后果"),
        ]
        package["discussion_questions"] = [
            {"level": "理解", "question": "请按时间线区分无争议事实、双方主张和待证事实。", "teaching_intent": "建立法律事实结构"},
            {"level": "分析", "question": "产能、验收和尾款条款之间形成怎样的权利义务关系？", "teaching_intent": "解释合同条款"},
            {"level": "分析", "question": "买方解除通知可能满足或欠缺哪些条件？卖方有哪些抗辩？", "teaching_intent": "形成双向规则适用"},
            {"level": "评价", "question": "双方损失主张分别需要哪些证据支持？", "teaching_intent": "评价举证与因果关系"},
            {"level": "创造", "question": "请形成一份包含争点、规则、事实、论证和救济的裁判提纲。", "teaching_intent": "完成法律论证"},
        ]
    else:
        return

    base_contract_keys = {
        "stochastic_programming": {"decision_stages", "random_variables", "scenarios", "decision_variables", "objective_function", "constraints", "solution_comparison"},
        "contract_law": {"jurisdiction", "parties", "clauses", "chronology", "legal_rules", "claims_defenses", "remedies"},
    }.get(contract_id, set())
    extra_elements = [item for item in blueprint.get("required_elements") or [] if item.get("key") not in base_contract_keys]
    for item in extra_elements:
        body["background"] += f" 教师确认本案例还必须使用“{item.get('label')}”：{item.get('planned_use')}。"
        segments.append(
            f"教师在蓝图中追加了“{item.get('label')}”要求：{item.get('planned_use')}。"
            "该要求必须进入学生的证据分析和最终产出，不能只在教学目标中出现。"
        )
    narrative_parts = list(segments)
    body["narrative"] = "\n\n".join(narrative_parts)
    minimum = int(task.target_words * 0.98)
    round_index = 0
    while count_case_body_chars(package) < minimum:
        label, use = evidence_topics[round_index % len(evidence_topics)]
        narrative_parts.append(
            f"第{round_index + 1}轮证据复核聚焦“{label}”。学生需要{use}，并把结论写入证据表。"
            "任何判断都必须指出所依据的信息、仍然缺失的材料以及结论改变的触发条件，不能用人物态度替代专业分析。"
        )
        body["narrative"] = "\n\n".join(narrative_parts)
        round_index += 1
    maximum = int(task.target_words * 1.05)
    actual = count_case_body_chars(package)
    if actual > maximum:
        other = count_case_body_chars({"body": {"background": body["background"], "decision_point": body["decision_point"]}})
        body["narrative"] = _truncate_visible_chars(body["narrative"], max(task.target_words - other, 900))

    package.setdefault("meta", {})["content_mode"] = "discipline_contract"
    package["meta"]["course_contract_id"] = contract_id
    package["case_blueprint"] = blueprint
    package["discipline_artifacts"] = artifacts
    evidence_markers = {
        "stochastic_programming": {
            "decision_stages": "决策过程拆成两个阶段", "random_variables": "随机变量、情景概率、决策变量和约束",
            "scenarios": "三个离散情景", "decision_variables": "一阶段变量x", "objective_function": "目标函数不是追求某个情景",
            "constraints": "平衡约束为x+y_s-z_s=d_s", "solution_comparison": "三套待选模型",
        },
        "contract_law": {
            "jurisdiction": "中国大陆法教学场景", "parties": "甲辰设备公司与海岳食品公司",
            "clauses": "合同第4条约定", "chronology": "5月8日设备运抵", "legal_rules": "合同法律规则为依据",
            "claims_defenses": "双方分别提出请求", "remedies": "继续履行、修理重作、解除合同或损害赔偿",
        },
    }.get(contract_id, {})
    package["discipline_coverage"] = [
        {
            "key": item.get("key"), "label": item.get("label"),
            "body_evidence": evidence_markers.get(item.get("key")) or str(item.get("planned_use") or "")[:60],
        }
        for item in blueprint.get("required_elements") or []
    ]
    package["domain_context"] = {
        "notes": "；".join(f"{item.get('label')}：{item.get('planned_use')}" for item in blueprint.get("required_elements") or [])
    }
    package["instructor_guide"] = {
        "teaching_flow": build_teaching_flow(int((task.config or {}).get("class_hours") or 2)),
        "key_points": [item.get("label") for item in blueprint.get("required_elements") or []][:6],
        "common_misconceptions": list(blueprint.get("forbidden_patterns") or []) or ["使用通用立场冲突替代专业分析"],
        "extension_reading": [],
    }


def build_structured_package(task: CaseTask, *, domain_notes: str | None = None) -> dict[str, Any]:
    """根据任务参数生成完整 CasePackage（无 LLM 时的高质量结构化产出）。"""
    profile = find_grounded_profile(task)
    if profile:
        return _build_grounded_package(task, profile)
    auto_research_pack = (task.config or {}).get("auto_research_pack") or {}
    preflight_error = generation_preflight_error(task) if not auto_research_pack else None
    if preflight_error:
        raise ValueError(preflight_error)
    lo_items = _objectives(task)
    title = task.title
    subject = task.subject
    course = task.course_name
    hours = int((task.config or {}).get("class_hours") or 2)
    special = (task.config or {}).get("special_requirements") or ""

    characters = [
        {"name": "陈启明", "role": "决策者/负责人", "stance": "倾向推进既定方案"},
        {"name": "林晓雯", "role": "中层协调者", "stance": "呼吁兼顾执行层反馈"},
        {"name": "赵磊", "role": "一线代表", "stance": "担忧节奏与资源不足"},
    ]
    material_query = f"{title} {subject} {course} {task.case_type}"
    visual_assets = recommended_materials(material_query, limit=RESOURCE_TARGET_COUNT)
    video_resources = recommended_videos(material_query, limit=RESOURCE_TARGET_COUNT)

    package: dict[str, Any] = {
        "meta": {
            "title": title,
            "subject": subject,
            "course": course,
            "difficulty": task.difficulty,
            "case_type": task.case_type,
            "target_audience": task.target_audience,
            "target_words": task.target_words,
            "fictional_disclaimer": "本案例为教学虚构情境，不代表任何真实企业或个人。",
        },
        "learning_objectives": lo_items,
        "body": {
            "background": (
                f"【背景】围绕「{title}」，某组织在{subject}实践中面临战略意图与一线执行的张力。"
                f"课程《{course}》面向{task.target_audience}学生，难度定位为{task.difficulty}。"
                f"{('教师补充要求：' + special) if special else ''}"
            ).strip(),
            "narrative": (
                f"【叙事】近期，组织围绕「{title}」召开关键协调会。"
                "陈启明强调窗口期与目标承诺，要求按原计划推进；"
                "林晓雯整理了跨部门反馈，指出沟通不足与节奏过快已引发抵触；"
                "赵磊代表执行层提出资源与能力准备不足，若强行推进可能影响质量与士气。"
                "会议中信息并不对称：决策层看到的是指标与外部压力，一线看到的是流程摩擦与加班负荷。"
                "冲突在是否调整推进节奏这一问题上集中爆发，各方立场公开化。"
                "现有材料无法直接导出唯一答案，各方必须公开判断依据，"
                "并为所选择的行动路径承担相应的机会成本与实施风险。"
            ),
            "decision_point": (
                f"在「{title}」情境下，决策者必须在会前明确："
                "（A）按原计划全面推进；（B）局部暂停并补齐沟通与培训；"
                "（C）调整目标与里程碑，换取执行层支持。请说明依据与风险。"
            ),
            "characters": characters,
        },
        "discussion_questions": [
            {
                "level": "理解",
                "question": f"案例中各方对「{title}」的核心诉求分别是什么？依据哪些事实？",
                "teaching_intent": "识别立场与信息来源",
            },
            {
                "level": "分析",
                "question": "冲突背后反映了哪些组织、管理或专业机制问题？",
                "teaching_intent": "穿透表象到结构因素",
            },
            {
                "level": "分析",
                "question": f"结合{subject}理论，如何解释林晓雯与赵磊的立场差异？",
                "teaching_intent": "理论迁移",
            },
            {
                "level": "评价",
                "question": "三种应对策略（全面推进/局部暂停/调整目标）的利弊如何评估？",
                "teaching_intent": "权衡决策标准",
            },
            {
                "level": "创造",
                "question": "若由你决策，将采取何种方案？请给出行动步骤与沟通计划。",
                "teaching_intent": "方案设计与课堂辩论",
            },
        ],
        "instructor_guide": {
            "teaching_flow": build_teaching_flow(hours),
            "key_points": [
                "利益相关方分析",
                "决策标准与风险权衡",
                f"{subject}相关理论视角",
            ],
            "common_misconceptions": [
                "将问题简化为单一技术或效率问题",
                "忽略一线信息与决策层信息的不对称",
            ],
            "extension_reading": [],
        },
        "alignment_matrix": [
            {
                "objective_id": lo["id"],
                "case_section": "决策点与角色立场" if i == 0 else "讨论题与汇报",
                "activity": "小组讨论" if i % 2 == 0 else "班级辩论",
                "assessment": "汇报点评",
            }
            for i, lo in enumerate(lo_items)
        ],
        "visual_assets": visual_assets,
        "evidence_sources": [],
        "video_resources": video_resources,
        "resource_targets": {
            "evidence_sources": RESOURCE_TARGET_COUNT,
            "official_visuals": RESOURCE_TARGET_COUNT,
            "recommended_visuals": RESOURCE_TARGET_COUNT,
            "videos": RESOURCE_TARGET_COUNT,
            "policy": "优先官方或高可信来源；数量不足时留空并提示，不以无关或不可核验内容凑数",
        },
        "material_research": {
            "context_signature": material_context_signature(title, subject, course, task.case_type),
            "query": material_query,
            "strategy": "course_scoped_official_catalog",
            "matched_count": len(visual_assets),
        },
        "quality": {},
    }
    if auto_research_pack:
        sources = deepcopy(auto_research_pack.get("sources") or [])
        package["meta"].update({
            "content_mode": "research_grounded",
            "fictional_disclaimer": "本案例依据公开来源生成；推断与教学任务不冒充已确认事实。",
            "source_policy": auto_research_pack.get("fact_policy"),
        })
        package["evidence_sources"] = [
            {key: value for key, value in source.items() if key != "excerpt"}
            for source in sources
        ]
        package["research_brief"] = {
            "fact_policy": auto_research_pack.get("fact_policy"),
            "sources": sources,
        }
    approved_blueprint = (task.config or {}).get("approved_blueprint") or {}
    selected_id, _, exact_contract = select_course_contract({
        "title": task.title, "subject": task.subject, "course_name": task.course_name,
        "learning_objectives": task.learning_objectives or [],
    })
    if approved_blueprint:
        if not auto_research_pack:
            package.setdefault("meta", {})["content_mode"] = "discipline_contract"
        package["meta"]["course_contract_id"] = approved_blueprint.get("contract_id")
        package["case_blueprint"] = approved_blueprint
        package["domain_context"] = {
            "notes": "；".join(
                f"{item.get('label')}：{item.get('planned_use')}"
                for item in approved_blueprint.get("required_elements") or []
            )
        }
        if not auto_research_pack and exact_contract and approved_blueprint.get("contract_id") == selected_id:
            _apply_discipline_contract(package, task, approved_blueprint)
    if domain_notes:
        package["domain_context"] = {"notes": domain_notes.strip()}
    update_body_length_meta(package, task.target_words)
    score_package(package)
    return package


def merge_agent_output(package: dict[str, Any], agent: str, data: dict[str, Any]) -> dict[str, Any]:
    """将单个 Agent 的 JSON 产出合并进案例包。"""
    if agent == "CasePlanner":
        if data.get("learning_objectives"):
            package["learning_objectives"] = data["learning_objectives"]
        if data.get("outline"):
            body = package.setdefault("body", {})
            body["background"] = data["outline"].get("background", body.get("background", ""))
            body["decision_point"] = data["outline"].get("decision_point", body.get("decision_point", ""))
            if data["outline"].get("characters"):
                body["characters"] = data["outline"]["characters"]
        if data.get("characters"):
            package.setdefault("body", {})["characters"] = data["characters"]
        if data.get("decision_point"):
            package.setdefault("body", {})["decision_point"] = data["decision_point"]
    elif agent == "DomainExpert":
        notes = data.get("domain_notes") or data.get("terminology") or ""
        if notes:
            package["domain_context"] = {
                "notes": str(notes).strip(),
                "discipline_checklist": data.get("discipline_checklist") or [],
            }
        if data.get("characters"):
            package.setdefault("body", {})["characters"] = data["characters"]
    elif agent == "CaseWriter":
        body = package.setdefault("body", {})
        for k in ("background", "narrative", "decision_point", "characters"):
            if data.get(k):
                body[k] = data[k]
        if data.get("body"):
            body.update({k: v for k, v in data["body"].items() if v})
        if data.get("discipline_coverage"):
            package["discipline_coverage"] = data["discipline_coverage"]
        if data.get("discipline_artifacts"):
            package["discipline_artifacts"] = data["discipline_artifacts"]
    elif agent == "PedagogyDesigner":
        if data.get("discussion_questions"):
            package["discussion_questions"] = data["discussion_questions"]
        if data.get("instructor_guide"):
            package["instructor_guide"] = data["instructor_guide"]
        if data.get("alignment_matrix"):
            package["alignment_matrix"] = data["alignment_matrix"]
    elif agent == "Reviewer":
        if data.get("quality"):
            package["quality"] = data["quality"]
        elif data.get("rubric_scores") or data.get("overall_score"):
            package["quality"] = {
                "rubric_scores": data.get("rubric_scores", {}),
                "reviewer_summary": data.get("reviewer_summary", ""),
                "overall_score": data.get("overall_score", 0),
                "issues": data.get("issues", []),
            }
        else:
            score_package(package)
    return normalize_case_package(package)
