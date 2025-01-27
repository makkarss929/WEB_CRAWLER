import json

class CrawlerMetrics:
    def __init__(self):
        self.stats = {
            'urls_crawled': 0,
            'product_urls': 0,
            'avg_response_time': 0,
            'error_rate': 0
        }

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if k in self.stats:
                self.stats[k] += v

    def report(self):
        return json.dumps(self.stats, indent=2)