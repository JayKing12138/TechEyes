"""增强实体图谱关系 - 添加实体间的复杂关系"""

from neo4j import GraphDatabase
from config import get_config
import hashlib

config = get_config()

uri = config.graph.uri
username = config.graph.username
password = config.graph.password

print(f"正在连接到 {uri}...")

driver = GraphDatabase.driver(uri, auth=(username, password))

# 定义实体间的关系规则
entity_relations = [
    {
        "from_entity": "OpenAI",
        "to_entity": "GPT-5",
        "relation_type": "DEVELOPED",
        "properties": {"since": "2024-01", "status": "released"}
    },
    {
        "from_entity": "OpenAI",
        "to_entity": "GPT-4",
        "relation_type": "DEVELOPED",
        "properties": {"since": "2023-03", "status": "active"}
    },
    {
        "from_entity": "OpenAI",
        "to_entity": "Sam Altman",
        "relation_type": "LED_BY",
        "properties": {"role": "CEO"}
    },
    {
        "from_entity": "GPT-5",
        "to_entity": "GPT-4",
        "relation_type": "EVOLVED_FROM",
        "properties": {"improvement": "多模态能力大幅提升"}
    },
    {
        "from_entity": "GPT-5",
        "to_entity": "多模态AI",
        "relation_type": "USES_TECHNOLOGY",
        "properties": {}
    },
    {
        "from_entity": "特斯拉",
        "to_entity": "FSD",
        "relation_type": "DEVELOPED",
        "properties": {"since": "2020", "version": "V12"}
    },
    {
        "from_entity": "特斯拉",
        "to_entity": "Elon Musk",
        "relation_type": "LED_BY",
        "properties": {"role": "CEO"}
    },
    {
        "from_entity": "FSD",
        "to_entity": "自动驾驶",
        "relation_type": "USES_TECHNOLOGY",
        "properties": {}
    },
    {
        "from_entity": "FSD",
        "to_entity": "神经网络",
        "relation_type": "USES_TECHNOLOGY",
        "properties": {"approach": "端到端"}
    },
    {
        "from_entity": "苹果",
        "to_entity": "Vision Pro",
        "relation_type": "DEVELOPED",
        "properties": {"released": "2024-02"}
    },
    {
        "from_entity": "苹果",
        "to_entity": "Tim Cook",
        "relation_type": "LED_BY",
        "properties": {"role": "CEO"}
    },
    {
        "from_entity": "Vision Pro",
        "to_entity": "空间计算",
        "relation_type": "USES_TECHNOLOGY",
        "properties": {}
    },
    {
        "from_entity": "Google DeepMind",
        "to_entity": "AlphaFold",
        "relation_type": "DEVELOPED",
        "properties": {"version": "3.0"}
    },
    {
        "from_entity": "Google DeepMind",
        "to_entity": "Demis Hassabis",
        "relation_type": "LED_BY",
        "properties": {"role": "CEO"}
    },
    {
        "from_entity": "AlphaFold",
        "to_entity": "蛋白质折叠",
        "relation_type": "SOLVES_PROBLEM",
        "properties": {}
    },
    {
        "from_entity": "AlphaFold",
        "to_entity": "药物研发",
        "relation_type": "ENABLES",
        "properties": {}
    },
    {
        "from_entity": "NVIDIA",
        "to_entity": "H100",
        "relation_type": "DEVELOPED",
        "properties": {"released": "2022"}
    },
    {
        "from_entity": "NVIDIA",
        "to_entity": "Jensen Huang",
        "relation_type": "LED_BY",
        "properties": {"role": "CEO"}
    },
    {
        "from_entity": "H100",
        "to_entity": "AI芯片",
        "relation_type": "IS_PRODUCT_TYPE",
        "properties": {}
    },
    {
        "from_entity": "H100",
        "to_entity": "数据中心",
        "relation_type": "USED_IN",
        "properties": {}
    },
    {
        "from_entity": "Microsoft",
        "to_entity": "Copilot",
        "relation_type": "DEVELOPED",
        "properties": {}
    },
    {
        "from_entity": "Microsoft",
        "to_entity": "Satya Nadella",
        "relation_type": "LED_BY",
        "properties": {"role": "CEO"}
    },
    {
        "from_entity": "Copilot",
        "to_entity": "GPT-4 Turbo",
        "relation_type": "POWERED_BY",
        "properties": {}
    },
    {
        "from_entity": "Copilot",
        "to_entity": "Office 365",
        "relation_type": "INTEGRATED_WITH",
        "properties": {}
    },
    {
        "from_entity": "Meta",
        "to_entity": "Llama 3",
        "relation_type": "DEVELOPED",
        "properties": {"type": "开源"}
    },
    {
        "from_entity": "Meta",
        "to_entity": "Mark Zuckerberg",
        "relation_type": "LED_BY",
        "properties": {"role": "CEO"}
    },
    {
        "from_entity": "Llama 3",
        "to_entity": "开源AI",
        "relation_type": "BELONGS_TO",
        "properties": {}
    },
    {
        "from_entity": "Llama 3",
        "to_entity": "大语言模型",
        "relation_type": "IS_PRODUCT_TYPE",
        "properties": {}
    },
    {
        "from_entity": "Amazon",
        "to_entity": "AWS",
        "relation_type": "OWNS",
        "properties": {}
    },
    {
        "from_entity": "Amazon",
        "to_entity": "Andy Jassy",
        "relation_type": "LED_BY",
        "properties": {"role": "CEO"}
    },
    {
        "from_entity": "AWS",
        "to_entity": "Titan",
        "relation_type": "DEVELOPED",
        "properties": {}
    },
    {
        "from_entity": "Titan",
        "to_entity": "AI芯片",
        "relation_type": "IS_PRODUCT_TYPE",
        "properties": {}
    },
    {
        "from_entity": "字节跳动",
        "to_entity": "豆包",
        "relation_type": "DEVELOPED",
        "properties": {}
    },
    {
        "from_entity": "豆包",
        "to_entity": "大语言模型",
        "relation_type": "IS_PRODUCT_TYPE",
        "properties": {}
    },
    {
        "from_entity": "豆包",
        "to_entity": "中文AI",
        "relation_type": "SPECIALIZES_IN",
        "properties": {}
    },
    {
        "from_entity": "Anthropic",
        "to_entity": "Claude",
        "relation_type": "DEVELOPED",
        "properties": {}
    },
    {
        "from_entity": "Anthropic",
        "to_entity": "Dario Amodei",
        "relation_type": "LED_BY",
        "properties": {"role": "CEO"}
    },
    {
        "from_entity": "Claude",
        "to_entity": "AI安全",
        "relation_type": "FOCUSES_ON",
        "properties": {}
    },
    {
        "from_entity": "OpenAI",
        "to_entity": "Microsoft",
        "relation_type": "PARTNERED_WITH",
        "properties": {"investment": "100亿美元"}
    },
    {
        "from_entity": "OpenAI",
        "to_entity": "Anthropic",
        "relation_type": "COMPETES_WITH",
        "properties": {}
    },
    {
        "from_entity": "GPT-5",
        "to_entity": "Claude",
        "relation_type": "COMPETES_WITH",
        "properties": {}
    },
    {
        "from_entity": "GPT-5",
        "to_entity": "Llama 3",
        "relation_type": "COMPETES_WITH",
        "properties": {}
    },
    {
        "from_entity": "NVIDIA",
        "to_entity": "OpenAI",
        "relation_type": "SUPPLIES_TO",
        "properties": {"product": "H100 GPU"}
    },
    {
        "from_entity": "NVIDIA",
        "to_entity": "Microsoft",
        "relation_type": "SUPPLIES_TO",
        "properties": {"product": "H100 GPU"}
    },
    {
        "from_entity": "NVIDIA",
        "to_entity": "Meta",
        "relation_type": "SUPPLIES_TO",
        "properties": {"product": "H100 GPU"}
    },
    {
        "from_entity": "Amazon",
        "to_entity": "Anthropic",
        "relation_type": "INVESTED_IN",
        "properties": {"amount": "40亿美元"}
    },
    {
        "from_entity": "Google DeepMind",
        "to_entity": "Anthropic",
        "relation_type": "INVESTED_IN",
        "properties": {"amount": "40亿美元"}
    }
]

def make_entity_id(name: str, etype: str) -> str:
    key = f"{etype}::{name}".lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()

try:
    with driver.session() as session:
        print("\n开始添加实体间关系...\n")
        
        success_count = 0
        skip_count = 0
        
        for relation in entity_relations:
            from_entity_name = relation["from_entity"]
            to_entity_name = relation["to_entity"]
            relation_type = relation["relation_type"]
            properties = relation.get("properties", {})
            
            # 查找实体
            result = session.run(
                """
                MATCH (e1:Entity) WHERE e1.name = $from_name
                MATCH (e2:Entity) WHERE e2.name = $to_name
                RETURN e1, e2
                """,
                {"from_name": from_entity_name, "to_name": to_entity_name}
            )
            
            records = list(result)
            if len(records) == 0:
                print(f"⚠️  跳过: {from_entity_name} -> {to_entity_name} (实体不存在)")
                skip_count += 1
                continue
            
            # 创建关系
            props_str = ", ".join([f"r.{k} = ${k}" for k in properties.keys()])
            set_clause = f"SET {props_str}" if props_str else ""
            
            query = f"""
                MATCH (e1:Entity {{name: $from_name}})
                MATCH (e2:Entity {{name: $to_name}})
                MERGE (e1)-[r:{relation_type}]->(e2)
                {set_clause}
                RETURN e1.name, type(r) as rel_type, e2.name
            """
            
            result = session.run(query, {
                "from_name": from_entity_name,
                "to_name": to_entity_name,
                **properties
            })
            
            record = result.single()
            if record:
                print(f"✅ 创建关系: {record['e1.name']} -[{relation_type}]-> {record['e2.name']}")
                success_count += 1
        
        print(f"\n{'='*60}")
        print(f"✅ 成功创建 {success_count} 条实体关系")
        if skip_count > 0:
            print(f"⚠️  跳过 {skip_count} 条关系（实体不存在）")
        print(f"{'='*60}\n")
        
        # 统计关系数量
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        total_relations = result.single()['count']
        print(f"📊 数据库中总关系数: {total_relations}")
        
        # 按类型统计
        result = session.run("""
            MATCH ()-[r]->() 
            RETURN type(r) as rel_type, count(r) as count 
            ORDER BY count DESC
        """)
        
        print("\n关系类型统计:")
        for record in result:
            print(f"  - {record['rel_type']}: {record['count']} 条")
        
finally:
    driver.close()
    print("\n✅ 完成！")
