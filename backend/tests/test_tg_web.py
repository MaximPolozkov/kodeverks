from app.bot.sources.tg_web import normalize_username, parse_page

SAMPLE = """
<meta property="og:title" content="Заказы для фрилансеров">
<section class="tgme_channel_history">
<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="freelance_orders/101" data-view="x">
<div class="tgme_widget_message_text js-message_text" dir="auto">Нужен сайт для салона красоты,<br/>бюджет 60 тыс. Пишите <a href="https://t.me/ivan_client">@ivan</a></div>
</div></div>
<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message js-widget_message" data-post="freelance_orders/102">
<div class="tgme_widget_message_text js-message_text">Ещё заказы в чате t.me/web_jobs_chat &amp; s.me</div>
</div></div>
</section>
"""


def test_parse_page():
    page = parse_page("freelance_orders", SAMPLE)
    assert page.title == "Заказы для фрилансеров"
    assert [p.post_id for p in page.posts] == ["101", "102"]
    assert "Нужен сайт для салона красоты,\nбюджет 60 тыс." in page.posts[0].text
    assert "& s.me" in page.posts[1].text
    assert {"ivan_client", "web_jobs_chat"} <= page.mentioned


def test_normalize_username():
    assert normalize_username("https://t.me/s/freelance_orders") == "freelance_orders"
    assert normalize_username("@web_jobs_chat") == "web_jobs_chat"
    assert normalize_username("t.me/joinchat") is None
    assert normalize_username("ab") is None
