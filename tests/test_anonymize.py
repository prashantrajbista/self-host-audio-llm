"""CV anonymization: identifiers go, what the interview needs stays. Runs Presidio + spaCy locally, no network.
Run: python -m tests.test_anonymize
"""

from server.agent.anonymize import anonymize_cv

CV = """PRASHANT RAJ BISTA
prashant.bista.18@example.com | +977 981-234-5678 | linkedin.com/in/prashantbista | 12 Lakeside Road, Pokhara
Date of birth: 14 March 1996
GitHub: pbista18 | LinkedIn - prashant-bista-dev | github.com/pbista | Twitter @pbista_dev

Senior Software Engineer, Acme Payments (Jan 2021 - Present)
- Cut p99 checkout latency by 40% by moving the ledger to Kafka and Redis
- Built CI on Jenkins and Docker; mentored 4 engineers
Software Engineer, Globex Corp (2018 - 2020)
- Shipped ASP.NET and Node.js services to 2M users

Education: BSc Computer Science, Tribhuvan University (2014 - 2018)
Skills: Python, Kafka, Jenkins, Kubernetes, Terraform
References: available on request from Prashant Bista's manager"""


def main():
    out = anonymize_cv(CV)
    print(out)
    for gone in ["Prashant", "PRASHANT", "BISTA", "Bista", "example.com", "981", "linkedin", "Lakeside", "1996",
                 "pbista18", "prashant-bista-dev", "pbista", "@pbista_dev"]:
        assert gone not in out, gone
    for kept in ["Acme Payments", "Globex Corp", "Tribhuvan University", "Senior Software Engineer", "Jan 2021",
                 "40%", "Kafka", "Jenkins", "Redis", "ASP.NET", "Node.js", "2014 - 2018", "mentored 4 engineers"]:
        assert kept in out, kept
    for placeholder in ["[NAME]", "[EMAIL]", "[PHONE]", "[LINK]", "[DOB]"]:
        assert placeholder in out, placeholder
    # a title line isn't taken for a name
    assert "Curriculum Vitae" in anonymize_cv("Curriculum Vitae\n" + CV.split("\n", 1)[1])
    print("ok")


if __name__ == "__main__":
    main()
