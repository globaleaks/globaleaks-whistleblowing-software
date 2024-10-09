class VirusScanResult:
    def __init__(self, name, is_infected, viruses):
        self.name = name
        self.is_infected = is_infected
        self.viruses = viruses

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get('name'),
            is_infected=data.get('is_infected'),
            viruses=data.get('viruses', [])
        )