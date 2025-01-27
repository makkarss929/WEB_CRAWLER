# from collections import deque
# import re
#
# class PriorityFrontier:
#     PRIORITY_RULES = {
#         'high': [r'/p/', r'/product', r'/dp/'],
#         'medium': [r'/category', r'/collection'],
#         'low': [r'/about', r'/contact']
#     }
#
#     def __init__(self):
#         self.queues = {
#             'high': deque(),
#             'medium': deque(),
#             'low': deque()
#         }
#
#     def empty(self):
#         """Check if all queues are empty"""
#         return (
#                 len(self.queues['high']) == 0 and
#                 len(self.queues['medium']) == 0 and
#                 len(self.queues['low']) == 0
#         )
#
#     def add_url(self, url):
#         priority = self._classify_priority(url)
#         self.queues[priority].append(url)
#
#     def get_next(self):
#         for priority in ['high', 'medium', 'low']:
#             if self.queues[priority]:
#                 return self.queues[priority].popleft()
#         return None
#
#     def _classify_priority(self, url):
#         for pattern in self.PRIORITY_RULES['high']:
#             if re.search(pattern, url):
#                 return 'high'
#         for pattern in self.PRIORITY_RULES['medium']:
#             if re.search(pattern, url):
#                 return 'medium'
#         return 'low'



from collections import deque
import re

class PriorityFrontier:
    PRIORITY_RULES = {
        'high': [r'/p/', r'/product', r'/dp/'],
        'medium': [r'/category', r'/collection'],
        'low': [r'/about', r'/contact']
    }

    def __init__(self):
        self.queues = {
            'high': deque(),
            'medium': deque(),
            'low': deque()
        }

    def empty(self):
        """Check if all queues are empty"""
        return (
            len(self.queues['high']) == 0 and
            len(self.queues['medium']) == 0 and
            len(self.queues['low']) == 0
        )

    def add_url(self, url, priority=None):  # Add optional priority parameter
        """Add URL to the frontier with explicit or classified priority"""
        if priority is None:
            priority = self._classify_priority(url)
        self.queues[priority].append(url)

    def get_next(self):
        for priority in ['high', 'medium', 'low']:
            if self.queues[priority]:
                return self.queues[priority].popleft()
        return None

    def _classify_priority(self, url):
        """Classify priority if not explicitly provided"""
        for pattern in self.PRIORITY_RULES['high']:
            if re.search(pattern, url):
                return 'high'
        for pattern in self.PRIORITY_RULES['medium']:
            if re.search(pattern, url):
                return 'medium'
        return 'low'