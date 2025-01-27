from pybloom_live import ScalableBloomFilter


class VisitedURLTracker:
    def __init__(self):
        self.filter = ScalableBloomFilter(
            initial_capacity=1000,
            error_rate=0.001
        )

    def add(self, url):
        self.filter.add(url)

    def __contains__(self, url):
        return url in self.filter