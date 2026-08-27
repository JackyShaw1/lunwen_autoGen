"""按课程自动检索并构建带来源片段的事实资料包。"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.config import get_settings

BLOCKED_HOST_PARTS = ("wikipedia.org", "baike.baidu.com", "zhihu.com", "csdn.net", "blog", "douyin.com")
TRUSTED_DOMAIN_SUFFIXES = (
    "gov.cn", "edu.cn", "ac.cn", "people.com.cn", "news.cn",
    "xinhuanet.com", "cninfo.com.cn", "sse.com.cn", "szse.cn", "hkexnews.hk",
)


def _credibility(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if any(host == suffix or host.endswith(f".{suffix}") for suffix in TRUSTED_DOMAIN_SUFFIXES):
        return "A"
    return "B"


def _queries(task) -> list[str]:
    base = f"{task.title} {task.course_name} {task.subject}"
    return [
        f"{base} 真实案例 官方 实践",
        f"{base} site:gov.cn",
        f"{base} site:edu.cn OR site:ac.cn",
        f"{base} 新华网 人民网 央视网 权威报道",
        f"{base} 年报 公告 研究报告 实施成效",
    ]


async def build_auto_research_pack(task) -> dict:
    base_url = get_settings().searxng_url.rstrip("/")
    found: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=45.0) as client:
        responses: list[httpx.Response] = []
        # 元搜索后端会对短时间并发请求限流；按可信来源优先级串行检索更稳定。
        for query in _queries(task):
            try:
                response = await client.get(
                    f"{base_url}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "language": "zh-CN",
                        "safesearch": 1,
                        "categories": "general",
                    },
                )
            except httpx.HTTPError:
                continue
            responses.append(response)
            if response.status_code >= 400:
                continue
            for item in response.json().get("results") or []:
                url = str(item.get("url") or "").strip()
                host = (urlparse(url).hostname or "").lower()
                content = " ".join(str(item.get("content") or "").split())[:1600]
                if not url.startswith(("https://", "http://")) or not host or not content:
                    continue
                if any(part in host for part in BLOCKED_HOST_PARTS):
                    continue
                found.setdefault(url, {
                    "title": str(item.get("title") or host)[:300],
                    "source_page_url": url,
                    "source_org": host,
                    "published_at": str(item.get("publishedDate") or item.get("published_date") or "")[:30] or None,
                    "excerpt": content,
                    "credibility_tier": _credibility(url),
                    "search_engine": str(item.get("engine") or "searxng"),
                })
        if not responses:
            raise RuntimeError("内置检索服务不可用：全部检索请求均未获得响应")
    candidates = sorted(found.values(), key=lambda item: item["credibility_tier"])
    # 先保证来源机构多样性，再用同一机构的其他有效材料补足 10 条。
    ranked: list[dict] = []
    selected_hosts: set[str] = set()
    for item in candidates:
        if item["source_org"] not in selected_hosts:
            ranked.append(item)
            selected_hosts.add(item["source_org"])
        if len(ranked) == 10:
            break
    if len(ranked) < 10:
        selected_urls = {item["source_page_url"] for item in ranked}
        ranked.extend(item for item in candidates if item["source_page_url"] not in selected_urls)
        ranked = ranked[:10]
    if len(ranked) < 5:
        raise RuntimeError(f"自动研究只找到 {len(ranked)} 条可核验来源，低于生成门槛 5 条；请调整课程主题后重试")
    if sum(item["credibility_tier"] == "A" for item in ranked) < 2:
        raise RuntimeError("自动研究未找到至少 2 条政府、高校、科研机构、交易所或官方媒体来源，已停止生成以避免低可信拼接")
    if len({item["source_org"] for item in ranked}) < 3:
        raise RuntimeError("自动研究来源机构少于 3 家，交叉核验不足，已停止生成")
    for index, source in enumerate(ranked, 1):
        source["id"] = f"S{index}"
        source["usage"] = "用于案例事实核验；正文事实必须引用该来源编号"
    return {
        "query": f"{task.title} {task.course_name}",
        "provider": "self_hosted_searxng",
        "source_count": len(ranked),
        "sources": ranked,
        "fact_policy": "只能使用下列来源片段支持事实；不得将模型记忆写成事实；每项关键事实必须标注[S编号]。",
    }
