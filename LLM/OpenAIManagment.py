import json
from typing import List

from openai import OpenAI

from SQlDB.wallet import InsertIntoWallet
from config import EMBED_MODEL, LLM_MODEL, OPENAI_API_KEY

from typing import List, Optional

from qdrant_client import models

from Models.mainModels import SearchFilters
from prompts_config import SYSTEM_PROMPT, USER_PROMPT
# Initialize clients
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.gapgpt.app/v1"
)

def embed_query(text: str) -> List[float]:
    """تبدیل متن به embedding vector"""
    res = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return res.data[0].embedding
def createSummery(old_summary,new_user_msg,new_assistant_msg):
    summary_prompt = f"""
            با توجه به خلاصه قبلی مکالمه و پیام‌های جدید مبادله شده، یک خلاصه کوتاه، جامع و به زبان فارسی از کل مکالمه تا این لحظه بنویس. 
            جزئیات فنی مهم (مانند نام ابزارها، پورت‌ها، خطاها یا تصمیمات کلیدی) را حفظ کن اما خلاصه را تا حد امکان فشرده نگه‌دار.

            خلاصه قبلی:
            {old_summary}

            پیام‌های جدید:
            کاربر: {new_user_msg}
            دستیار: {new_assistant_msg}

            خلاصه جدید به‌روزشده:
            """

            # ۳. فراخوانی مدل برای خلاصه‌سازی (یک مدل سبک‌تر و سریع‌تر ترجیح داده می‌شود)
    response = client.responses.create(
                model=LLM_MODEL,  # یا یک مدل سریع‌تر/ارزان‌تر
                input=[{"role": "user", "content": summary_prompt}],
                temperature=0.3
            )
    return response.output_text.strip()
def CreateResponse(context,query,history,temperature):

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT.format(
                context=context,
                query=query,
                history=history
            )
        }
    ]
    response = client.responses.create(
        model=LLM_MODEL,
        input=messages,
        temperature=temperature
    )

    answer = response.output_text
    return response
def CreateResponseStreamWithMeta(context,userKey,background_tasks, query, history, temperature):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT.format(
                context=context,
                query=query,
                history=history
            )
        }
    ]

    # استفاده از context manager برای مدیریت صحیح اتصال استریم
    with client.responses.stream(
        model=LLM_MODEL,
        input=messages,
        temperature=temperature
    ) as stream:
        
        # ۱. ارسال فریم‌های متنی به صورت زنده
        for event in stream:
            if event.type == "response.output_text.delta":
                if event.delta:
                    yield {"type": "token", "content": event.delta}
        
        # ۲. پس از پایان دریافت متن، دریافت متادیتا از پاسخ نهایی
        # بسته به نسخه SDK مورد استفاده، شیء نهایی با متد یا ویژگی زیر قابل دریافت است:
        final_response = None
        if hasattr(stream, "get_final_response"):
            final_response = stream.get_final_response()
        elif hasattr(stream, "response"):
            final_response = stream.response

        # استخراج متادیتا در صورت وجود
        response_id = getattr(final_response, "id", None) if final_response else None
        usage = getattr(final_response, "usage", None) if final_response else None
      
        background_tasks.add_task(
                     
                    InsertIntoWallet,
                                         getattr(usage, "total_tokens", 0)*-1 if usage else 0,
                                         getattr(usage, "output_tokens", 0) if usage else 0,
                                         getattr(usage, "input_tokens", 0) if usage else 0,
                                         userKey,
                                         response_id,
                                     )
                   
        # yield {
        #     "type": "meta",
        #     "response_id": response_id,
        #     "usage": {
        #         "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
        #         "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        #         "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0
        #     }
        # }

def CreateResponseStream(context, query, history, temperature):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT.format(
                context=context,
                query=query,
                history=history
            )
        }
    ]

    with client.responses.stream(
        model=LLM_MODEL,
        input=messages,
        temperature=temperature
    ) as stream:
        for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta

def CreateResponseWithInput(messages,temperature):

    # messages = [
    #     {"role": "system", "content": SYSTEM_PROMPT},
    #     {
    #         "role": "user",
    #         "content": USER_PROMPT.format(
    #             context=context,
    #             query=query,
    #             history=history
    #         )
    #     }
    # ]
    response = client.responses.create(
        model=LLM_MODEL,
        input=messages,
        temperature=temperature
    )

    answer = response.output_text
    return response
def rerank_results(query, results):
    if not results:
        return results

    # فقط داده لازم را برای مدل می‌فرستیم
    candidates = []
   
    
    
    for r in results:
        payload= r.payload or {}
        metadata = payload.get("metadata") or {}
        imgs_info = metadata.get("imgs_info") or []
        # گرفتن نام تمام تصاویر موجود در لیست
        images = [img.get("image_name", "") for img in imgs_info if img.get("image_name")]

        candidates.append({
        "id": str(r.id),#dict:r.get("id")
        "text": payload.get("text", ""),
        "title": payload.get("title", ""),
        "score": float(r.score or 0.0),
        "heading": payload.get("heading") or "",
        "date": payload.get("date") or "",
        "tags": payload.get("tags") or [],
        "keywords": payload.get("keywords") or [],
        "source_file": payload.get("source_file") or "",
        "image": images,
    })


    system_prompt = """
You are a reranking assistant.

Given a user query and a list of retrieved results, return ONLY a valid JSON array.
Each item must contain:
- id
- score

Scoring rules:
- score must be a float between 0.0 and 1.0
- higher score means more relevant
- first identify the single most relevant document/source for answering the query
- strongly prefer chunks from that same document/source if they are relevant to the query
- rank chunks from other documents lower unless they are clearly more relevant than the chunks from the primary document
- prefer a coherent set of results from one document over a mixed set from multiple weakly related documents
- penalize irrelevant or off-topic chunks, especially those matching only generic technical terms
- do not boost content about different devices, subsystems, or topics unless the query explicitly asks for them

Output rules:
- return only valid JSON
- do not return explanations
- each item must have exactly:
  - "id"
  - "score"
""".strip()





    user_prompt = f"""
Query:
{query}

Results:
{json.dumps(candidates, ensure_ascii=False, indent=2)}#درست خواندن متن فارسی:ensure_ascii=False
#, indent=2 خروچی چند خطی و مرتب میشه

Return only JSON like:
[
  {{"id": "1", "score": 0.95}},
  {{"id": "2", "score": 0.40}}
]
""".strip()

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content#برای گرفتن متن واقعی پاسخ مدل
        scored_items = json.loads(content)#این متن JSON را تبدیل کن به داده واقعی پایتون

        # map از id به score جدید
        score_map = {}
        for item in scored_items:
            rid = str(item.get("id"))
            score = float(item.get("score", 0.0))
            score = max(0.0, min(1.0, score))  # clamp
            score_map[rid] = score

        # score جدید را روی همان results اصلی اعمال می‌کنیم
        for r in results:
            # if isinstance(r, dict):
            #     rid = str(r["id"])
            #     if rid in score_map:
            #         r["score"] = score_map[rid]
            # else:
                rid = str(r.id)
                if rid in score_map:
                    r.score = score_map[rid]

        # sort نهایی نزولی
        results.sort(
            key=lambda r: r["score"] if isinstance(r, dict) else r.score,
            reverse=True
        )

        return results

    except Exception as e:
        print(f"Rerank failed: {e}")
        return results
def CreateResponseStreamGeneral(query,userKey, background_tasks):
    messages = [
        {
            "role": "system",
            "content": (
                "تو فقط مجاز به پاسخ‌دادن به سلام، احوالپرسی، تشکر، و خداحافظی هستی. "
                "در این موارد، پاسخ را کوتاه، طبیعی، و محاوره‌ای به فارسی بده. "
                "اگر پیام هر چیز دیگری بود، یا شامل سوالات سیاسی، امنیتی، یا اقتصادی بود، "
                "فقط و فقط این جمله را بگو: "
                "من تنها مجاز به پاسخگویی به سوالات مربوط به داکیومنت شرکت آدونیس هستم."
            ),
        },
        {
            "role": "user",
            "content": query,
        },
    ]

    # استفاده از context manager برای مدیریت صحیح اتصال استریم
    with client.responses.stream(
        model=LLM_MODEL,
        input=messages,
        temperature=0.1
    ) as stream:
        
        # ۱. ارسال فریم‌های متنی به صورت زنده
        for event in stream:
            if event.type == "response.output_text.delta":
                if event.delta:
                    yield {"type": "token", "content": event.delta}
        
        # ۲. پس از پایان دریافت متن، دریافت متادیتا از پاسخ نهایی
        final_response = None
        if hasattr(stream, "get_final_response"):
            final_response = stream.get_final_response()
        elif hasattr(stream, "response"):
            final_response = stream.response

        # استخراج متادیتا در صورت وجود
        response_id = getattr(final_response, "id", None) if final_response else None
        usage = getattr(final_response, "usage", None) if final_response else None
      
        # اضافه کردن تسک ثبت تراکنش به پس‌زمینه
        background_tasks.add_task(
            InsertIntoWallet,
            getattr(usage, "total_tokens", 0) * -1 if usage else 0,
            getattr(usage, "output_tokens", 0) if usage else 0,
            getattr(usage, "input_tokens", 0) if usage else 0,
            userKey,
            response_id,
        )
        
        # در صورت نیاز به ارسال متادیتا به کلاینت در انتهای استریم، می‌توانید کامنت زیر را باز کنید:
        # yield {
        #     "type": "meta",
        #     "response_id": response_id,
        #     "usage": {
        #         "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
        #         "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        #         "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0
        #     }
        # }


def detect_intent(query: str) -> str:
    resp =client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": """
You are a classifier.

Classify the user's query as exactly one of these two labels:

1. technical
   Use this label only if the query is related to banking equipment or its software/services, including topics such as:
   ATM, kiosk, self-service banking machines, card reader, pinpad, printer, dispenser, recycler, cash handling, device errors, troubleshooting, installation, setup, configuration, maintenance, monitoring, or operation.

2. general
   Use this label for anything else, including:
   greetings, small talk, thanks, goodbyes, political questions, economic questions, security-related questions, and any query not related to banking equipment.

Reply with one word only:
technical
or
general
"""},
            {"role": "user", "content": query}
        ],
        max_tokens=5,
        temperature=0
    )
    return resp.choices[0].message.content.strip().lower()
