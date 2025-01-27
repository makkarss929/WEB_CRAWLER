class VisitedURLTracker:
    def __init__(self):
        self.seen_urls = set()

    def add(self, url):
        self.seen_urls.add(url)

    def __contains__(self, url):
        return url in self.seen_urls