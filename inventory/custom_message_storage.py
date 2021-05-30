from django.contrib.messages.storage.session import SessionStorage
from django.contrib.messages.storage.base import Message
from itertools import chain


class DedupMessageMixin(object):
    def add(self, level, message, extra_tags):    
        messages = chain(self._loaded_messages, self._queued_messages)
        for m in messages:
            if m.message == message:
                return
        return super(DedupMessageMixin, self).add(level, message, extra_tags)

class MyMessageStorage(DedupMessageMixin, SessionStorage):
    pass 