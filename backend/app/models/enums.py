from enum import StrEnum


class UserRole(StrEnum):
    admin = "admin"
    manager = "manager"


class ServiceType(StrEnum):
    website = "website"
    bot = "bot"
    crm = "crm"
    app = "app"


class OrderStatus(StrEnum):
    new = "new"
    in_progress = "in_progress"
    negotiation = "negotiation"
    done = "done"
    rejected = "rejected"


class OrderSource(StrEnum):
    site = "site"
    bot = "bot"
    utm = "utm"


class LeadSource(StrEnum):
    vk = "vk"
    telegram = "telegram"
    web = "web"


class LeadStatus(StrEnum):
    found = "found"
    contacted = "contacted"
    replied = "replied"
    qualified = "qualified"
    converted = "converted"
    lost = "lost"
    opted_out = "opted_out"


class MessageDirection(StrEnum):
    incoming = "in"
    outgoing = "out"


class ContactChannel(StrEnum):
    email = "email"
    telegram = "telegram"
    vk = "vk"
    whatsapp = "whatsapp"
    phone = "phone"
