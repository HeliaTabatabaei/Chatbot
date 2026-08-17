import os

def append_image_urls_to_maintext(
    maintext: str,
    imgs_info: list,
    image_base_url: str
) -> str:
    """
    متن اصلی را بدون تغییر حفظ می‌کند و فقط لینک تصاویر را به انتهای آن اضافه می‌کند.
    پسوند تصاویر به صورت داینامیک از 'image_name' استخراج می‌شود.
    """
    if not maintext or not imgs_info:
        return maintext

    base_url = image_base_url.rstrip("/")
    image_links = []
    added_rids = set()

    for img in imgs_info:
        r_id = img.get("rId")
        image_name = img.get("image_name", "")

        if not r_id or r_id in added_rids:
            continue
        
        # استخراج پسوند از image_name (مثال: image1.jpg -> .jpg)
        _, ext = os.path.splitext(image_name)
        
        # اگر به هر دلیلی پسوندی پیدا نشد، یک مقدار پیش‌فرض در نظر بگیرید (یا خالی بگذارید)
        if not ext:
            ext = ".png" # مقدار پیش‌فرض ایمن

        # ساخت URL با rId و پسوند استخراج شده
        # فرض بر این است که نام فایل روی سرور با rId مطابقت دارد
        url = f"{base_url}/{r_id}{ext}"
        caption = img.get("caption") or f"تصویر {r_id}"

        image_links.append(f"[{caption}]: {url}")
        added_rids.add(r_id)

    if not image_links:
        return maintext

    # الحاق به انتهای متن بدون دستکاری OCR قبلی
    return f"{maintext}\n\n---\n\n### لینک تصاویر:\n\n" + "\n".join(image_links)
