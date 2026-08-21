"""任务参数驱动的教学案例四件套构建（Mock / LLM 后处理共用）"""

from __future__ import annotations

import re
from typing import Any

from app.models import CaseTask
from app.services.rubric_service import score_package


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


def normalize_case_package(package: dict[str, Any]) -> dict[str, Any]:
    """Remove legacy internal annotations from student-facing text and preserve them once."""
    body = package.setdefault("body", {})
    background = str(body.get("background") or "")
    if "【学科注释】" not in background:
        return package

    parts = re.split(r"\s*【学科注释】\s*", background)
    body["background"] = parts[0].strip()
    existing_context = package.get("domain_context") or {}
    existing_notes = (
        existing_context.get("notes", "")
        if isinstance(existing_context, dict)
        else str(existing_context)
    )
    candidates = [existing_notes, *parts[1:]]
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


def build_structured_package(task: CaseTask, *, domain_notes: str | None = None) -> dict[str, Any]:
    """根据任务参数生成完整 CasePackage（无 LLM 时的高质量结构化产出）。"""
    lo_items = _objectives(task)
    title = task.title
    subject = task.subject
    course = task.course_name
    hours = (task.config or {}).get("class_hours") or 2
    special = (task.config or {}).get("special_requirements") or ""

    characters = [
        {"name": "陈启明", "role": "决策者/负责人", "stance": "倾向推进既定方案"},
        {"name": "林晓雯", "role": "中层协调者", "stance": "呼吁兼顾执行层反馈"},
        {"name": "赵磊", "role": "一线代表", "stance": "担忧节奏与资源不足"},
    ]

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
            "teaching_flow": (
                f"建议 {hours} 课时：阅读案例(20min)→小组讨论决策点(25min)"
                "→班级汇报与教师点评(20min)→总结对齐教学目标(余下时间)"
            ),
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
        "quality": {},
    }
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
            package["domain_context"] = {"notes": str(notes).strip()}
        if data.get("characters"):
            package.setdefault("body", {})["characters"] = data["characters"]
    elif agent == "CaseWriter":
        body = package.setdefault("body", {})
        for k in ("background", "narrative", "decision_point", "characters"):
            if data.get(k):
                body[k] = data[k]
        if data.get("body"):
            body.update({k: v for k, v in data["body"].items() if v})
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
