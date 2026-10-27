from sqlalchemy import select

from app.bot import dialog
from app.bot.runner import save_post_as_lead
from app.bot.scoring import score_text
from app.bot.sources import FoundPost
from app.bot.sources.telegram import parse_update
from app.models import BotMessage, BotStopList, Lead, LeadSource, LeadStatus, ServiceType
from app.schemas.bot import BotSettingsData


class FakeSource:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    async def send_message(self, author_id: str, text: str) -> None:
        self.sent.append((author_id, text))


def test_scoring_relevant_request():
    score = score_text(
        "Ищу разработчика, нужен сайт для салона красоты, бюджет 80 тыс",
        ["нужен сайт", "ищу разработчика"],
        ["вакансия"],
    )
    assert score.value >= 70
    assert score.service == ServiceType.website


def test_scoring_stop_word_blocks():
    score = score_text("Вакансия: ищу разработчика сайтов в штат", ["ищу разработчика"], ["вакансия"])
    assert score.blocked and score.value == 0


def test_opt_out_and_ready_detection():
    assert dialog.wants_out("Стоп")
    assert dialog.wants_out("не интересно, спасибо")
    assert not dialog.wants_out("Сколько стоит лендинг?")
    assert dialog.is_ready("Хорошо, как заказать?")
    assert dialog.is_ready("Я готов оформить заказ")


def test_first_message_always_discloses_bot():
    lead = Lead(request_text="Нужен телеграм бот для записи", service_guess=ServiceType.bot)
    config = BotSettingsData(first_message_template="Привет! Делаем {service}.")
    text = dialog.first_message(lead, config)
    assert "автоматический помощник" in text
    assert "стоп" in text.lower()


def test_parse_telegram_private():
    kind, post = parse_update(
        {"message": {"message_id": 1, "text": "Привет", "chat": {"id": 42, "type": "private"},
                     "from": {"id": 42, "first_name": "Олег"}}}
    )
    assert kind == "private"
    assert post.author_external_id == "42"
    assert post.can_contact


async def test_save_post_dedup_and_threshold(session):
    config = BotSettingsData(min_score=40)
    post = FoundPost(
        source=LeadSource.vk,
        external_id="10_20",
        text="Нужен сайт для кофейни, ищу разработчика, срок месяц",
        author_external_id="10",
    )
    first = await save_post_as_lead(session, post, config)
    assert first is not None
    assert await save_post_as_lead(session, post, config) is None

    weak = FoundPost(source=LeadSource.vk, external_id="10_21", text="Котики")
    assert await save_post_as_lead(session, weak, config) is None


async def test_incoming_opt_out_adds_to_stoplist(session, monkeypatch):
    fake = FakeSource()
    monkeypatch.setattr(dialog, "get_source", lambda *_: fake)
    post = FoundPost(
        source=LeadSource.vk, external_id="dm_7", text="Не пишите мне", author_external_id="7"
    )
    reply = await dialog.handle_incoming(session, post)
    assert reply is None
    assert fake.sent == []
    lead = await session.scalar(select(Lead))
    assert lead.status == LeadStatus.opted_out
    assert await session.scalar(select(BotStopList)) is not None


async def test_incoming_ready_sends_order_link(session, monkeypatch):
    fake = FakeSource()
    monkeypatch.setattr(dialog, "get_source", lambda *_: fake)
    post = FoundPost(
        source=LeadSource.telegram,
        external_id="dm_9",
        text="Нужен бот для записи клиентов. Как заказать?",
        author_external_id="9",
    )
    reply = await dialog.handle_incoming(session, post)
    assert reply is not None
    lead = await session.scalar(select(Lead))
    assert f"lead_id={lead.public_token}" in reply
    assert "#order" in reply
    assert lead.status == LeadStatus.qualified
    assert fake.sent and fake.sent[0][0] == "9"
    messages = list(await session.scalars(select(BotMessage).order_by(BotMessage.id)))
    assert [m.direction for m in messages] == ["in", "out"]


async def test_manual_mode_bot_stays_silent(session, monkeypatch):
    fake = FakeSource()
    monkeypatch.setattr(dialog, "get_source", lambda *_: fake)
    lead = Lead(
        source=LeadSource.vk,
        external_id="dm_5",
        author_external_id="5",
        request_text="",
        relevance_score=0,
        status=LeadStatus.replied,
        can_contact=True,
        manual_mode=True,
        public_token="t5",
    )
    session.add(lead)
    await session.commit()
    post = FoundPost(source=LeadSource.vk, external_id="dm_5", text="Ещё вопрос", author_external_id="5")
    assert await dialog.handle_incoming(session, post) is None
    assert fake.sent == []
