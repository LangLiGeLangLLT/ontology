from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

# ====================== 1. 定义命名空间 ======================
# 教育本体命名空间
EDU = Namespace("http://example.org/edu-ontology#")

# 创建RDF图，本体全部三元组放在这个图里
g = Graph()

# 绑定前缀，方便序列化输出
g.bind("edu", EDU)
g.bind("owl", OWL)
g.bind("rdfs", RDFS)
g.bind("rdf", RDF)
g.bind("xsd", XSD)

# ====================== 2. 定义本体本身（Ontology声明） ======================
edu_onto = URIRef("http://example.org/edu-ontology")
g.add((edu_onto, RDF.type, OWL.Ontology))
g.add((edu_onto, RDFS.label, Literal("教育领域本体", lang="zh")))
g.add((edu_onto, RDFS.comment, Literal("简单教育本体：课程、教师、学生", lang="zh")))

# ====================== 3. 定义OWL类（Class） ======================
# 教师类 Teacher
g.add((EDU.Teacher, RDF.type, OWL.Class))
g.add((EDU.Teacher, RDFS.label, Literal("教师", lang="zh")))
g.add((EDU.Teacher, RDFS.comment, Literal("授课教师", lang="zh")))

# 学生类 Student
g.add((EDU.Student, RDF.type, OWL.Class))
g.add((EDU.Student, RDFS.label, Literal("学生", lang="zh")))

# 课程类 Course
g.add((EDU.Course, RDF.type, OWL.Class))
g.add((EDU.Course, RDFS.label, Literal("课程", lang="zh")))

# ====================== 4. 定义对象属性 ObjectProperty（连接两个实例） ======================
# hasTeacher：课程拥有教师，域是Course，范围是Teacher
g.add((EDU.hasTeacher, RDF.type, OWL.ObjectProperty))
g.add((EDU.hasTeacher, RDFS.domain, EDU.Course))
g.add((EDU.hasTeacher, RDFS.range, EDU.Teacher))
g.add((EDU.hasTeacher, RDFS.label, Literal("拥有教师", lang="zh")))

# hasStudent：课程拥有学生
g.add((EDU.hasStudent, RDF.type, OWL.ObjectProperty))
g.add((EDU.hasStudent, RDFS.domain, EDU.Course))
g.add((EDU.hasStudent, RDFS.range, EDU.Student))
g.add((EDU.hasStudent, RDFS.label, Literal("拥有学生", lang="zh")))

# ====================== 5. 定义数据属性 DatatypeProperty（关联字面量：字符串、数字） ======================
# teacherName：教师姓名
g.add((EDU.teacherName, RDF.type, OWL.DatatypeProperty))
g.add((EDU.teacherName, RDFS.domain, EDU.Teacher))
g.add((EDU.teacherName, RDFS.range, XSD.string))
g.add((EDU.teacherName, RDFS.label, Literal("教师姓名", lang="zh")))

# courseName：课程名称
g.add((EDU.courseName, RDF.type, OWL.DatatypeProperty))
g.add((EDU.courseName, RDFS.domain, EDU.Course))
g.add((EDU.courseName, RDFS.range, XSD.string))

# studentName：学生姓名
g.add((EDU.studentName, RDF.type, OWL.DatatypeProperty))
g.add((EDU.studentName, RDFS.domain, EDU.Student))
g.add((EDU.studentName, RDFS.range, XSD.string))

# ====================== 6. 创建本体实例（个体 Individual） ======================
# 实例：人工智能课程
ai_course = EDU.AICourse
g.add((ai_course, RDF.type, EDU.Course))
g.add((ai_course, EDU.courseName, Literal("人工智能导论", lang="zh")))

# 实例：张老师
teacher_zhang = EDU.TeacherZhang
g.add((teacher_zhang, RDF.type, EDU.Teacher))
g.add((teacher_zhang, EDU.teacherName, Literal("张三", lang="zh")))

# 实例：学生李四
student_li = EDU.StudentLi
g.add((student_li, RDF.type, EDU.Student))
g.add((student_li, EDU.studentName, Literal("李四", lang="zh")))

# 实例关系：AI课程 hasTeacher 张老师；AI课程 hasStudent 李四
g.add((ai_course, EDU.hasTeacher, teacher_zhang))
g.add((ai_course, EDU.hasStudent, student_li))

# ====================== 7. 查询本体数据 SPARQL ======================
print("===== SPARQL 查询：所有课程名称及授课教师 =====")
query = """
PREFIX edu: <http://example.org/edu-ontology#>
SELECT ?courseName ?teacherName
WHERE {
    ?course a edu:Course ;
            edu:courseName ?courseName ;
            edu:hasTeacher ?teacher .
    ?teacher edu:teacherName ?teacherName .
}
"""
for row in g.query(query):
    print(f"课程：{row.courseName}，教师：{row.teacherName}")

# ====================== 8. 导出本体文件（Turtle格式，可Protege打开） ======================
turtle_str = g.serialize(format="turtle", encoding="utf-8").decode("utf-8")
with open("edu_ontology.ttl", "w", encoding="utf-8") as f:
    f.write(turtle_str)

print("\n===== 本体Turtle片段输出 =====")
print(turtle_str[:1200])
print("\n本体已保存到 edu_ontology.ttl，可以用 Protege 直接打开编辑！")
