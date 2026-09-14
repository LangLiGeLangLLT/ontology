"""
金融知识本体构建（Financial Knowledge Ontology）
使用 rdflib 以 OWL/RDFS 方式定义类、属性、个体与层级关系，输出 Turtle 文件。
"""
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL, XSD

# ---------- 1. 命名空间 ----------
FIN = Namespace("http://example.org/finance#")
g = Graph()

# 绑定前缀，便于序列化阅读
g.bind("fin", FIN)
g.bind("owl", OWL)
g.bind("rdfs", RDFS)
g.bind("rdf", RDF)
g.bind("xsd", XSD)

# 声明本体文档
g.add((FIN.FinancialOntology, RDF.type, OWL.Ontology))
g.add((FIN.FinancialOntology, RDFS.label,
       Literal("金融知识本体", lang="zh")))
g.add((FIN.FinancialOntology, RDFS.comment,
       Literal("覆盖金融机构、证券、市场、行业、投资者与宏观指标的本体。", lang="zh")))


def klass(uri, parent=None, label=None, comment=None):
    """便捷地声明一个 OWL 类及其层级与中文标签。"""
    g.add((uri, RDF.type, OWL.Class))
    if parent is not None:
        g.add((uri, RDFS.subClassOf, parent))
    if label:
        g.add((uri, RDFS.label, Literal(label, lang="zh")))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="zh")))


def obj_prop(uri, domain, range_, inverse=None):
    """声明对象属性。"""
    g.add((uri, RDF.type, OWL.ObjectProperty))
    g.add((uri, RDFS.domain, domain))
    g.add((uri, RDFS.range, range_))
    if inverse:
        g.add((uri, OWL.inverseOf, inverse))


def data_prop(uri, domain, range_):
    """声明数据属性。"""
    g.add((uri, RDF.type, OWL.DatatypeProperty))
    g.add((uri, RDFS.domain, domain))
    g.add((uri, RDFS.range, range_))


# ---------- 2. 类层级 ----------
# 金融工具
klass(FIN.FinancialInstrument, label="金融工具", comment="可交易的金融资产合约")
klass(FIN.Security, FIN.FinancialInstrument, label="证券")
klass(FIN.Stock, FIN.Security, label="股票")
klass(FIN.Bond, FIN.Security, label="债券")
klass(FIN.Fund, FIN.Security, label="基金")
klass(FIN.ETF, FIN.Fund, label="交易型开放式指数基金")
klass(FIN.MutualFund, FIN.Fund, label="公募基金")
klass(FIN.Derivative, FIN.Security, label="衍生品")
klass(FIN.Option, FIN.Derivative, label="期权")
klass(FIN.Future, FIN.Derivative, label="期货")

# 金融机构
klass(FIN.FinancialInstitution, label="金融机构")
klass(FIN.Bank, FIN.FinancialInstitution, label="银行")
klass(FIN.InsuranceCompany, FIN.FinancialInstitution, label="保险公司")
klass(FIN.Broker, FIN.FinancialInstitution, label="券商")
klass(FIN.FundManager, FIN.FinancialInstitution, label="基金管理人")

# 市场 / 交易所
klass(FIN.Market, label="金融市场")
klass(FIN.StockExchange, FIN.Market, label="证券交易所")

# 其它核心概念
klass(FIN.Company, label="公司（发行人）")
klass(FIN.Industry, label="行业")
klass(FIN.Investor, label="投资者")
klass(FIN.IndividualInvestor, FIN.Investor, label="个人投资者")
klass(FIN.InstitutionalInvestor, FIN.Investor, label="机构投资者")
klass(FIN.Region, label="地区/市场板块")

# 互斥声明（OWL 推理用）
g.add((FIN.Bank, OWL.disjointWith, FIN.InsuranceCompany))
g.add((FIN.Stock, OWL.disjointWith, FIN.Bond))

# ---------- 3. 对象属性 ----------
obj_prop(FIN.issues, FIN.FinancialInstitution, FIN.FinancialInstrument,
         inverse=FIN.issuedBy)                       # 发行 -> 被发行
obj_prop(FIN.listedOn, FIN.Security, FIN.StockExchange)  # 上市于
obj_prop(FIN.belongsToIndustry, FIN.Company, FIN.Industry)
obj_prop(FIN.belongsToRegion, FIN.Security, FIN.Region)
obj_prop(FIN.hasUnderlying, FIN.Derivative, FIN.FinancialInstrument)  # 标的
obj_prop(FIN.investsIn, FIN.Investor, FIN.FinancialInstrument)
obj_prop(FIN.tradedOn, FIN.Market, FIN.FinancialInstrument)
obj_prop(FIN.headquarteredIn, FIN.Company, FIN.Region)

# ---------- 4. 数据属性 ----------
data_prop(FIN.hasTicker, FIN.Security, XSD.string)        # 交易代码
data_prop(FIN.hasISIN, FIN.Security, XSD.string)          # ISIN 编码
data_prop(FIN.hasMarketCap, FIN.Company, XSD.decimal)     # 市值（亿元）
data_prop(FIN.hasLatestPrice, FIN.Security, XSD.decimal)  # 最新价
data_prop(FIN.hasYield, FIN.Bond, XSD.decimal)            # 收益率
data_prop(FIN.foundedYear, FIN.FinancialInstitution, XSD.gYear)

# ---------- 5. 个体（示例数据） ----------
# 行业
g.add((FIN.Baijiu, RDF.type, FIN.Industry))
g.add((FIN.Baijiu, RDFS.label, Literal("白酒行业", lang="zh")))
g.add((FIN.Banking, RDF.type, FIN.Industry))
g.add((FIN.Banking, RDFS.label, Literal("银行业", lang="zh")))

# 地区
g.add((FIN.AShare, RDF.type, FIN.Region))
g.add((FIN.AShare, RDFS.label, Literal("A股市场", lang="zh")))
g.add((FIN.HShare, RDF.type, FIN.Region))
g.add((FIN.HShare, RDFS.label, Literal("港股市场", lang="zh")))

# 交易所
g.add((FIN.SSE, RDF.type, FIN.StockExchange))
g.add((FIN.SSE, RDFS.label, Literal("上海证券交易所", lang="zh")))
g.add((FIN.SZSE, RDF.type, FIN.StockExchange))
g.add((FIN.SZSE, RDFS.label, Literal("深圳证券交易所", lang="zh")))

# 公司：贵州茅台
g.add((FIN.Moutai, RDF.type, FIN.Company))
g.add((FIN.Moutai, RDFS.label, Literal("贵州茅台", lang="zh")))
g.add((FIN.Moutai, FIN.belongsToIndustry, FIN.Baijiu))
g.add((FIN.Moutai, FIN.hasMarketCap, Literal(21000, datatype=XSD.decimal)))

# 股票
g.add((FIN.Moutai_Stock, RDF.type, FIN.Stock))
g.add((FIN.Moutai_Stock, RDFS.label, Literal("贵州茅台(600519)", lang="zh")))
g.add((FIN.Moutai_Stock, FIN.hasTicker, Literal("600519")))
g.add((FIN.Moutai_Stock, FIN.hasISIN, Literal("CNE0000004R9")))
g.add((FIN.Moutai_Stock, FIN.listedOn, FIN.SSE))
g.add((FIN.Moutai_Stock, FIN.belongsToRegion, FIN.AShare))
g.add((FIN.Moutai_Stock, FIN.hasLatestPrice, Literal(1680.00, datatype=XSD.decimal)))

# 银行：工商银行
g.add((FIN.ICBC, RDF.type, FIN.Bank))
g.add((FIN.ICBC, RDFS.label, Literal("中国工商银行", lang="zh")))
g.add((FIN.ICBC, FIN.foundedYear, Literal(1984, datatype=XSD.gYear)))
g.add((FIN.ICBC, FIN.belongsToIndustry, FIN.Banking))

g.add((FIN.ICBC_Stock, RDF.type, FIN.Stock))
g.add((FIN.ICBC_Stock, RDFS.label, Literal("工商银行(601398)", lang="zh")))
g.add((FIN.ICBC_Stock, FIN.hasTicker, Literal("601398")))
g.add((FIN.ICBC_Stock, FIN.listedOn, FIN.SSE))
g.add((FIN.ICBC_Stock, FIN.issues, FIN.ICBC))

# 债券示例
g.add((FIN.GB_2025, RDF.type, FIN.Bond))
g.add((FIN.GB_2025, RDFS.label, Literal("2025年记账式国债", lang="zh")))
g.add((FIN.GB_2025, FIN.hasYield, Literal(0.0245, datatype=XSD.decimal)))

# ETF 示例
g.add((FIN.CSI300_ETF, RDF.type, FIN.ETF))
g.add((FIN.CSI300_ETF, RDFS.label, Literal("沪深300ETF", lang="zh")))
g.add((FIN.CSI300_ETF, FIN.hasTicker, Literal("510300")))

# ---------- 6. 序列化 ----------
out = "/home/user/Doubao/chats/38441724921905922/finance_ontology.ttl"
g.serialize(destination=out, format="turtle")
print(f"本体已生成: {out}")
print(f"三元组总数: {len(g)}")
#（注：内容由AI生成）
