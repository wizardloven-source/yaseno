# core/domain/sites/entities.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Any
from uuid import UUID

from .value_objects import SiteId, SiteCode, SiteType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Site:
    """
    AGGREGATE ROOT - الموقع
    نظام مستقل لإدارة المواقع، يمكن ربطه بأي كيان آخر لاحقاً
    """

    id: SiteId = field(default_factory=SiteId.generate)
    code: SiteCode = field(default_factory=lambda: SiteCode(""))
    name: str = ""
    site_type: SiteType = SiteType.GENERAL

    # العنوان
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"

    # معلومات الاتصال
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    fax: Optional[str] = None

    # معلومات إضافية
    contact_person: Optional[str] = None
    contact_position: Optional[str] = None
    tax_number: Optional[str] = None
    notes: Optional[str] = None
    working_hours: Optional[str] = None

    # الإحداثيات
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # الحالة
    is_active: bool = True
    is_default: bool = False
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    # بيانات التدقيق
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = ""
    version: int = 1

    _events: List[Any] = field(default_factory=list, repr=False)

    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        if self.city:
            return f"{self.code} - {self.name} ({self.city})"
        return f"{self.code} - {self.name}"

    @property
    def full_address(self) -> str:
        """العنوان الكامل"""
        parts = [self.street, self.city, self.country]
        return ", ".join([p for p in parts if p])

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        site_type: str = "general",
        street: Optional[str] = None,
        city: Optional[str] = None,
        country: str = "LB",
        phone: Optional[str] = None,
        mobile: Optional[str] = None,
        email: Optional[str] = None,
        contact_person: Optional[str] = None,
        notes: Optional[str] = None,
        is_default: bool = False,
        created_by: str = ""
    ) -> 'Site':
        """إنشاء موقع جديد"""
        site = cls(
            code=SiteCode(code),
            name=name,
            site_type=SiteType(site_type),
            street=street,
            city=city,
            country=country,
            phone=phone,
            mobile=mobile,
            email=email,
            contact_person=contact_person,
            notes=notes,
            is_default=is_default,
            is_active=True,
            created_by=created_by,
            updated_by=created_by,
            version=1
        )

        from .events import SiteCreatedEvent
        site._events.append(SiteCreatedEvent(
            site_id=site.id,
            site_code=site.code.value,
            site_name=site.name,
            site_type=site.site_type.value,
            created_by=created_by
        ))

        return site

    def update(
        self,
        name: Optional[str] = None,
        site_type: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        phone: Optional[str] = None,
        mobile: Optional[str] = None,
        email: Optional[str] = None,
        contact_person: Optional[str] = None,
        notes: Optional[str] = None,
        working_hours: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        is_active: Optional[bool] = None,
        updated_by: str = ""
    ) -> None:
        """تحديث بيانات الموقع"""
        changes = {}

        if name is not None and name != self.name:
            changes['name'] = {'old': self.name, 'new': name}
            self.name = name

        if site_type is not None:
            new_type = SiteType(site_type)
            if new_type != self.site_type:
                changes['site_type'] = {'old': self.site_type.value, 'new': new_type.value}
                self.site_type = new_type

        if street is not None and street != self.street:
            changes['street'] = {'old': self.street, 'new': street}
            self.street = street

        if city is not None and city != self.city:
            changes['city'] = {'old': self.city, 'new': city}
            self.city = city

        if country is not None and country != self.country:
            changes['country'] = {'old': self.country, 'new': country}
            self.country = country

        if phone is not None and phone != self.phone:
            changes['phone'] = {'old': self.phone, 'new': phone}
            self.phone = phone

        if mobile is not None and mobile != self.mobile:
            changes['mobile'] = {'old': self.mobile, 'new': mobile}
            self.mobile = mobile

        if email is not None and email != self.email:
            changes['email'] = {'old': self.email, 'new': email}
            self.email = email

        if contact_person is not None and contact_person != self.contact_person:
            changes['contact_person'] = {'old': self.contact_person, 'new': contact_person}
            self.contact_person = contact_person

        if notes is not None and notes != self.notes:
            changes['notes'] = {'old': self.notes, 'new': notes}
            self.notes = notes

        if working_hours is not None and working_hours != self.working_hours:
            changes['working_hours'] = {'old': self.working_hours, 'new': working_hours}
            self.working_hours = working_hours

        if latitude is not None and latitude != self.latitude:
            changes['latitude'] = {'old': self.latitude, 'new': latitude}
            self.latitude = latitude

        if longitude is not None and longitude != self.longitude:
            changes['longitude'] = {'old': self.longitude, 'new': longitude}
            self.longitude = longitude

        if is_active is not None and is_active != self.is_active:
            changes['is_active'] = {'old': self.is_active, 'new': is_active}
            self.is_active = is_active

        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            self.version += 1

            from .events import SiteUpdatedEvent
            self._events.append(SiteUpdatedEvent(
                site_id=self.id,
                changes=changes,
                updated_by=updated_by
            ))

    def soft_delete(self, deleted_by: str) -> None:
        """حذف ناعم للموقع"""
        if not self.is_deleted:
            self.is_deleted = True
            self.is_active = False
            self.deleted_at = utc_now()
            self.deleted_by = deleted_by
            self.updated_at = utc_now()
            self.updated_by = deleted_by
            self.version += 1

            from .events import SiteDeletedEvent
            self._events.append(SiteDeletedEvent(
                site_id=self.id,
                site_code=self.code.value,
                site_name=self.name,
                deleted_by=deleted_by
            ))

    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events
