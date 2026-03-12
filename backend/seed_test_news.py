"""生成测试新闻数据（用于演示）"""

import asyncio
import hashlib
from datetime import datetime, timedelta
import random

test_news_data = [
    {
        "title": "OpenAI发布GPT-5：多模态能力大幅提升，支持实时视频理解",
        "url": "https://example.com/news/gpt5-release",
        "snippet": "OpenAI今日正式发布GPT-5模型，在多模态理解、推理能力和长文本处理方面取得重大突破。新模型支持实时视频理解和更复杂的逻辑推理任务。",
        "content": "OpenAI今日正式发布GPT-5模型，这是继GPT-4之后的又一重大突破。新模型在多个方面实现了显著提升：\n\n1. 多模态能力：支持实时视频理解，可以分析视频内容并回答相关问题\n2. 推理能力：在复杂逻辑推理任务上表现更出色\n3. 长文本处理：支持最多100K token的上下文窗口\n4. 实时更新：可以访问最新信息并进行实时分析\n\n业内专家认为，GPT-5的发布将进一步推动AI技术在各个领域的应用。",
        "source": "TechCrunch",
        "entities": [
            {"name": "OpenAI", "type": "company", "salience": 0.95},
            {"name": "GPT-5", "type": "product", "salience": 0.90},
            {"name": "GPT-4", "type": "product", "salience": 0.70},
            {"name": "多模态AI", "type": "technology", "salience": 0.75},
            {"name": "Sam Altman", "type": "person", "salience": 0.60}
        ]
    },
    {
        "title": "特斯拉FSD V12正式推送：完全自动驾驶时代来临",
        "url": "https://example.com/news/tesla-fsd-v12",
        "snippet": "特斯拉开始向全球用户推送FSD V12版本，实现了真正的端到端神经网络自动驾驶，无需高精地图支持。",
        "content": "特斯拉今日宣布开始向全球用户推送FSD（Full Self-Driving）V12版本。这是特斯拉自动驾驶技术的重大里程碑，实现了完全基于神经网络的端到端自动驾驶。\n\n主要特点：\n1. 端到端神经网络：不再依赖传统的规则编码，完全由AI学习驾驶行为\n2. 无需高精地图：可以在任何道路上工作，不依赖预先绘制的地图\n3. 实时决策：能够处理复杂的交通场景和突发情况\n4. 持续学习：通过车队数据不断优化驾驶策略\n\n马斯克表示，这是通往完全自动驾驶的关键一步。",
        "source": "Electrek",
        "entities": [
            {"name": "特斯拉", "type": "company", "salience": 0.95},
            {"name": "FSD", "type": "product", "salience": 0.90},
            {"name": "Elon Musk", "type": "person", "salience": 0.85},
            {"name": "自动驾驶", "type": "technology", "salience": 0.80},
            {"name": "神经网络", "type": "technology", "salience": 0.70}
        ]
    },
    {
        "title": "苹果Vision Pro销量不及预期，库克回应：这是长期投资",
        "url": "https://example.com/news/apple-vision-pro-sales",
        "snippet": "苹果Vision Pro上市三个月销量未达预期，蒂姆·库克在财报会议上表示，空间计算是苹果的长期战略投资。",
        "content": "苹果公司今日发布季度财报，Vision Pro销量成为焦点。据报道，Vision Pro上市三个月以来的销量约为20万台，低于分析师预期的30万台。\n\n在财报会议上，蒂姆·库克回应了市场关切：\n1. 长期战略：空间计算是苹果的未来，Vision Pro是重要布局\n2. 开发者生态：已有超过1000个原生应用\n3. 企业市场：正在与多家企业合作开发行业应用\n4. 未来规划：将继续改进产品并扩大应用场景\n\n分析师认为，高昂的价格和有限的应用场景是销量不佳的主要原因。",
        "source": "Bloomberg",
        "entities": [
            {"name": "苹果", "type": "company", "salience": 0.95},
            {"name": "Vision Pro", "type": "product", "salience": 0.90},
            {"name": "Tim Cook", "type": "person", "salience": 0.85},
            {"name": "空间计算", "type": "technology", "salience": 0.75},
            {"name": "AR/VR", "type": "technology", "salience": 0.70}
        ]
    },
    {
        "title": "谷歌DeepMind推出AlphaFold 3：蛋白质结构预测再突破",
        "url": "https://example.com/news/alphafold-3",
        "snippet": "DeepMind发布AlphaFold 3，不仅能预测蛋白质结构，还能预测蛋白质与其他分子的相互作用，加速药物研发。",
        "content": "谷歌DeepMind今日宣布推出AlphaFold 3，这是蛋白质结构预测领域的又一重大突破。\n\n主要进展：\n1. 多分子预测：可以预测蛋白质与DNA、RNA、小分子药物的相互作用\n2. 精度提升：在多个基准测试中准确率超过90%\n3. 药物研发：显著加速新药发现和开发过程\n4. 开放访问：继续向全球科学家免费开放\n\nDeepMind CEO Demis Hassabis表示，AlphaFold 3将帮助科学家更好地理解生命过程，并加速疾病治疗方法的发现。",
        "source": "Nature",
        "entities": [
            {"name": "Google DeepMind", "type": "company", "salience": 0.95},
            {"name": "AlphaFold", "type": "product", "salience": 0.90},
            {"name": "Demis Hassabis", "type": "person", "salience": 0.80},
            {"name": "蛋白质折叠", "type": "technology", "salience": 0.85},
            {"name": "药物研发", "type": "technology", "salience": 0.75}
        ]
    },
    {
        "title": "英伟达市值突破2万亿美元，AI芯片需求持续强劲",
        "url": "https://example.com/news/nvidia-market-cap",
        "snippet": "英伟达市值首次突破2万亿美元，成为全球第三大科技公司。AI芯片需求持续强劲，H100芯片供不应求。",
        "content": "英伟达股价今日大涨，市值首次突破2万亿美元，成为继苹果和微软之后全球第三大科技公司。\n\n关键数据：\n1. 股价表现：年内涨幅超过80%\n2. 营收增长：数据中心业务同比增长超过400%\n3. 产品需求：H100 AI芯片供不应求，订单排到2025年\n4. 市场地位：在AI训练芯片市场占有率达90%\n\nCEO黄仁勋表示，AI正处于拐点，生成式AI的兴起推动了对计算能力的巨大需求。",
        "source": "Reuters",
        "entities": [
            {"name": "NVIDIA", "type": "company", "salience": 0.95},
            {"name": "H100", "type": "product", "salience": 0.85},
            {"name": "Jensen Huang", "type": "person", "salience": 0.80},
            {"name": "AI芯片", "type": "technology", "salience": 0.90},
            {"name": "数据中心", "type": "technology", "salience": 0.70}
        ]
    },
    {
        "title": "微软Copilot全面升级：集成GPT-4 Turbo，支持更复杂任务",
        "url": "https://example.com/news/microsoft-copilot-upgrade",
        "snippet": "微软宣布Copilot全面升级，集成GPT-4 Turbo模型，支持更长的上下文和更复杂的任务处理。",
        "content": "微软今日宣布对其AI助手Copilot进行全面升级，为用户带来更强大的功能。\n\n升级内容：\n1. 模型升级：集成GPT-4 Turbo，响应速度提升50%\n2. 上下文扩展：支持128K token上下文窗口\n3. 多模态能力：支持图像理解和生成\n4. 深度集成：与Office套件更紧密集成\n5. 个性化：支持记忆用户偏好和工作习惯\n\n微软CEO纳德拉表示，Copilot正在重新定义生产力工具，让每个人都能拥有AI助手。",
        "source": "The Verge",
        "entities": [
            {"name": "Microsoft", "type": "company", "salience": 0.95},
            {"name": "Copilot", "type": "product", "salience": 0.90},
            {"name": "Satya Nadella", "type": "person", "salience": 0.75},
            {"name": "GPT-4 Turbo", "type": "product", "salience": 0.85},
            {"name": "Office 365", "type": "product", "salience": 0.70}
        ]
    },
    {
        "title": "Meta发布Llama 3：开源大模型新标杆，性能媲美GPT-4",
        "url": "https://example.com/news/meta-llama-3",
        "snippet": "Meta发布Llama 3开源大模型，提供70B和400B两个版本，在多项基准测试中性能接近或超越GPT-4。",
        "content": "Meta今日正式发布Llama 3开源大语言模型，为开源AI社区带来重大利好。\n\n模型规格：\n1. Llama 3 70B：适合大多数应用场景\n2. Llama 3 400B：旗舰版本，性能媲美GPT-4\n3. 开源协议：允许商业使用\n4. 多语言支持：支持超过100种语言\n\n性能表现：\n- MMLU基准测试：接近GPT-4水平\n- 代码生成：超越同级别模型\n- 推理能力：在复杂任务上表现出色\n\n扎克伯格表示，开源是推动AI发展的最佳方式，Meta将继续投资开源AI生态。",
        "source": "TechCrunch",
        "entities": [
            {"name": "Meta", "type": "company", "salience": 0.95},
            {"name": "Llama 3", "type": "product", "salience": 0.90},
            {"name": "Mark Zuckerberg", "type": "person", "salience": 0.80},
            {"name": "开源AI", "type": "technology", "salience": 0.85},
            {"name": "大语言模型", "type": "technology", "salience": 0.75}
        ]
    },
    {
        "title": "亚马逊推出Titan系列AI芯片，挑战英伟达霸主地位",
        "url": "https://example.com/news/amazon-titan-chips",
        "snippet": "亚马逊AWS推出自研Titan系列AI芯片，性能媲美英伟达H100，成本降低40%，加速云服务AI化。",
        "content": "亚马逊AWS今日宣布推出自研的Titan系列AI芯片，直接挑战英伟达在AI芯片市场的霸主地位。\n\n产品规格：\n1. Titan Train：专为AI训练设计\n2. Titan Infer：针对推理任务优化\n3. 性能：训练速度媲美H100，推理速度更快\n4. 成本：比同类产品低40%\n5. 能效：功耗降低30%\n\n战略意义：\n- 减少对英伟达的依赖\n- 降低AWS AI服务成本\n- 提供差异化竞争优势\n\nAWS CEO Andy Jassy表示，自研芯片是AWS长期战略的重要组成部分。",
        "source": "Wired",
        "entities": [
            {"name": "Amazon", "type": "company", "salience": 0.95},
            {"name": "AWS", "type": "company", "salience": 0.90},
            {"name": "Titan", "type": "product", "salience": 0.85},
            {"name": "Andy Jassy", "type": "person", "salience": 0.75},
            {"name": "AI芯片", "type": "technology", "salience": 0.80}
        ]
    },
    {
        "title": "字节跳动发布豆包大模型：中文能力领先，支持超长上下文",
        "url": "https://example.com/news/bytedance-doubao",
        "snippet": "字节跳动正式发布豆包大模型，在中文理解和生成能力上表现优异，支持300万token超长上下文。",
        "content": "字节跳动今日正式发布自研大模型豆包，在中文AI领域带来新的竞争者。\n\n核心能力：\n1. 中文理解：在多项中文基准测试中领先\n2. 超长上下文：支持300万token上下文窗口\n3. 多模态：支持文本、图像、视频理解\n4. 实时性：可以访问最新信息\n\n应用场景：\n- 智能客服\n- 内容创作\n- 教育辅导\n- 企业办公\n\n字节跳动表示，豆包大模型已经在其多个产品中应用，服务数亿用户。",
        "source": "36氪",
        "entities": [
            {"name": "字节跳动", "type": "company", "salience": 0.95},
            {"name": "豆包", "type": "product", "salience": 0.90},
            {"name": "大语言模型", "type": "technology", "salience": 0.85},
            {"name": "中文AI", "type": "technology", "salience": 0.80},
            {"name": "多模态", "type": "technology", "salience": 0.70}
        ]
    },
    {
        "title": "Anthropic获得40亿美元融资，估值达180亿美元",
        "url": "https://example.com/news/anthropic-funding",
        "snippet": "AI安全公司Anthropic完成40亿美元融资，估值达到180亿美元，将用于扩大Claude模型研发和商业化。",
        "content": "AI安全公司Anthropic今日宣布完成新一轮40亿美元融资，公司估值达到180亿美元。\n\n融资详情：\n1. 领投方：Google、Salesforce Ventures\n2. 估值：180亿美元\n3. 用途：扩大Claude模型研发和商业化\n\n公司背景：\n- 由前OpenAI员工创立\n- 专注于AI安全和对齐问题\n- Claude模型在多个领域表现优异\n\nCEO Dario Amodei表示，这笔资金将帮助Anthropic加速AI安全研究，确保AI系统的可靠性和可控性。",
        "source": "Wall Street Journal",
        "entities": [
            {"name": "Anthropic", "type": "company", "salience": 0.95},
            {"name": "Claude", "type": "product", "salience": 0.90},
            {"name": "Dario Amodei", "type": "person", "salience": 0.80},
            {"name": "AI安全", "type": "technology", "salience": 0.85},
            {"name": "Google", "type": "company", "salience": 0.75}
        ]
    }
]


def make_news_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def make_entity_id(name: str, etype: str) -> str:
    key = f"{etype}::{name}".lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


async def seed_test_data():
    """将测试数据写入Neo4j"""
    try:
        from services.neo4j_client import neo4j_client
        from datetime import datetime, timedelta
        import random
        
        print("开始写入测试数据到Neo4j...")
        
        for idx, news in enumerate(test_news_data):
            news_id = make_news_id(news["url"])
            created_at = (datetime.utcnow() - timedelta(hours=random.randint(0, 72))).isoformat()
            
            print(f"[{idx + 1}/{len(test_news_data)}] 写入新闻: {news['title'][:50]}...")
            
            neo4j_client.run_query(
                """
                MERGE (n:News {id: $id})
                SET n.title = $title,
                    n.url = $url,
                    n.snippet = $snippet,
                    n.content = $content,
                    n.source = $source,
                    n.created_at = datetime($created_at)
                """,
                {
                    "id": news_id,
                    "title": news["title"],
                    "url": news["url"],
                    "snippet": news["snippet"],
                    "content": news["content"],
                    "source": news["source"],
                    "created_at": created_at,
                },
                read_only=False,
            )
            
            for entity in news.get("entities", []):
                entity_id = make_entity_id(entity["name"], entity["type"])
                
                neo4j_client.run_query(
                    """
                    MERGE (e:Entity {id: $eid})
                    SET e.name = $name,
                        e.type = $type
                    WITH e
                    MATCH (n:News {id: $nid})
                    MERGE (n)-[r:MENTIONS]->(e)
                    SET r.salience = $salience
                    """,
                    {
                        "eid": entity_id,
                        "nid": news_id,
                        "name": entity["name"],
                        "type": entity["type"],
                        "salience": entity["salience"],
                    },
                    read_only=False,
                )
        
        print(f"\n✅ 成功写入 {len(test_news_data)} 条测试新闻数据！")
        
        result = neo4j_client.run_query("MATCH (n:News) RETURN count(n) as count")
        print(f"📊 数据库中共有 {result[0]['count']} 条新闻")
        
        result = neo4j_client.run_query("MATCH (e:Entity) RETURN count(e) as count")
        print(f"📊 数据库中共有 {result[0]['count']} 个实体")
        
    except Exception as e:
        print(f"❌ 写入测试数据失败: {e}")
        print("\n请确保：")
        print("1. Neo4j服务已启动")
        print("2. .env中已配置NEO4J_URI、NEO4J_USERNAME、NEO4J_PASSWORD")
        print("3. 已安装neo4j Python包: pip install neo4j")


if __name__ == "__main__":
    asyncio.run(seed_test_data())
