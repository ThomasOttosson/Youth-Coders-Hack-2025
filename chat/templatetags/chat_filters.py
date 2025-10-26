from django import template

register = template.Library()

@register.filter
def other_participant(room, user):
    """Template filter to get other participant in direct messages"""
    if room.room_type == 'direct' and room.participants.count() == 2:
        return room.participants.exclude(id=user.id).first()
    return None