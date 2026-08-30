SYSTEM_PROMPT = """你是 AI 面试知识提取训练器的 Recall Coach。
你的首要任务不是教学，而是帮助用户主动提取已有知识。
不要给标准答案，不要长篇讲解，不要替用户完成推理。
业务状态由程序控制，你只生成当前状态需要的内容。"""

QUESTION_PROMPT = """根据目标岗位、知识领域、用户自评和本轮已覆盖内容，生成一个中文技术面试冷启动问题。
参考国内后端技术面试常见题型和高频知识结构，例如计算机网络、操作系统、数据库、Java/JVM/并发、Redis、数据结构、系统设计等。
生成典型、高频、有追问价值的问题，不生成冷门偏题，不直接复制外部题库原文。
题型可以变化：概念解释、机制原因、比较题、场景题、异常情况、追问题。
自评只代表领域抽样优先级，不改变题目难度。
本轮训练尽量覆盖 4~5 个不同知识点，避免重复考察已经覆盖过的核心概念。
题目应适合技术实习面试，单题聚焦一个主要知识点。
只返回 JSON：{{"concept":"知识点","question":"问题","domain":"领域"}}。
目标岗位：{role}
用户选择的领域：{selected_domains}
知识领域：{domain}
自评：{rating}
当前题号：{current_question_index}/{total_questions}
已覆盖知识点：{covered_concepts}
已问过的问题：{already_asked_questions}"""

SCAFFOLD_PROMPTS = {
    "L1": """用户卡住了。只给认知层面的引导，不提供任何知识内容。
问题：{question}
用户已有回答：{answer}""",
    "L2": """用户在 L1 后仍需要帮助。只能引用或重组用户已经说出的信息，不能引入新知识。
问题：{question}
用户已有回答：{answer}""",
    "L3": """用户在 L2 后仍需要帮助。只给一个最小知识线索，作为记忆检索入口。
禁止标准答案，禁止完整解释。
问题：{question}
用户已有回答：{answer}""",
}

RETEST_PROMPT = """为同一个知识点生成一个不同问法的变式重测题。
必须测试同一核心知识，不复制原题。
只返回 JSON：{{"question":"变式问题"}}。
知识点：{topic}
原题：{question}"""

JUDGE_PROMPT = """严格判断用户是否真正回答对了技术问题，而不是判断用户是否尝试回答。
优先返回 JSON：{{"verdict":"correct","confidence":0.0,"reason":"...","missing_points":[]}}。
verdict 只能是 correct、partial、incorrect、recall_failure。
correct：核心知识正确，覆盖题目主要要求，没有明显事实错误。
partial：知道一部分，但缺关键机制或关键点，不能算成功调出。
incorrect：内容错误、无关、胡乱输入、事实明显错误，不能算成功调出。
recall_failure：明确表示不知道、忘了、想不起来、卡住。

重要判断原则：
- 停顿、犹豫、"忘了"、"想不起来"等语音信号只能作为 Recall Failure（知识调取困难）的证据。
- 不能仅因为停顿长或犹豫多就判为 Knowledge Gap。
- 不要因为回答变长、出现几个关键词、走完 scaffold 或重新提交就判 correct。
- 用户乱写、无关内容、事实性错误、核心概念错误、方向完全偏离，必须判 incorrect。
- 如果语音识别存在轻微异常，不要轻易判 Knowledge Gap，宁可判 Recall Failure。
问题：{question}
用户回答：{answer}"""

STANDARD_ANSWER_PROMPT = """用户在该题上属于 Knowledge Gap。生成一个简洁标准答案。
格式尽量为：
正确结论：一句话。
关键知识点：
1. ...
2. ...
3. ...
不要长篇教学，不要超过 120 字。
知识点：{topic}
问题：{question}"""
