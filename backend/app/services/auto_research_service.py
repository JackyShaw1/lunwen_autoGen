"""按课程自动检索并构建带来源片段的事实资料包。"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.services.runtime_research_service import get_research_config

BLOCKED_HOST_PARTS = ("wikipedia.org", "baike.baidu.com", "zhihu.com", "csdn.net", "blog", "douyin.com")
TRUSTED_HOST_PARTS = (
    ".gov.cn", ".edu.cn", ".ac.cn", "gov.cn", "people.com.cn", "news.cn",
    "xinhuanet.com", "cninfo.com.cn", "sse.com.cn", "szse.cn", "hkexnews.hk",
)


def _credibility(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if any(part in host for part in TRUSTED_HOST_PARTS):
        return "A"
    return "B"


def _queries(task) -> list[str]:
    base = f"{task.title} {task.course_name} {task.subject}"
    return [
        f"{base} 真实企业 实践 官网",
        f"{base} 企业案例 年报 流程 变革",
        f"{base} 权威媒体 研究报告 实施成效",
    ]


async def build_auto_research_pack(task) -> dict:
    config = get_research_config()
    if not config.available:
        raise RuntimeError("系统尚未配置自动事实研究服务，请管理员在“大模型配置”中启用自动资料研究")
    found: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=45.0) as client:
        for query in _queries(task):
            response = await client.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                json={
                    "query": query,
                    "search_depth": "basic",
                    "topic": "general",
                    "max_results": 10,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            if response.status_code >= 400:
                raise RuntimeError(f"自动检索服务返回 HTTP {response.status_code}，请管理员检查检索配置")
            for item in response.json().get("results") or []:
                url = str(item.get("url") or "").strip()
                host = (urlparse(url).hostname or "").lower()
                content = " ".join(str(item.get("content") or "").split())[:1600]
                if not url.startswith("https://") or not host or not content:
                    continue
                if any(part in host for part in BLOCKED_HOST_PARTS):
                    continue
                found.setdefault(url, {
                    "title": str(item.get("title") or host)[:300],
                    "source_page_url": url,
                    "source_org": host,
                    "published_at": str(item.get("published_date") or "")[:30] or None,
                    "excerpt": content,
                    "credibility_tier": _credibility(url),
                })
    ranked = sorted(found.values(), key=lambda item: (item["credibility_tier"], item["source_org"]))[:10]
    if len(ranked) < 5:
        raise RuntimeError(f"自动研究只找到 {len(ranked)} 条可核验来源，低于生成门槛 5 条；请调整课程主题后重试")
    if sum(item["credibility_tier"] == "A" for item in ranked) < 2:
        raise RuntimeError("自动研究未找到至少 2 条政府、高校、科研机构、交易所或官方媒体来源，已停止生成以避免低可信拼接")
    for index, source in enumerate(ranked, 1):
        source["id"] = f"S{index}"
        source["usage"] = "用于案例事实核验；正文事实必须引用该来源编号"
    return {
        "query": f"{task.title} {task.course_name}",
        "provider": "tavily",
        "source_count": len(ranked),
        "sources": ranked,
        "fact_policy": "只能使用下列来源片段支持事实；不得将模型记忆写成事实；每项关键事实必须标注[S编号]。",
    }
