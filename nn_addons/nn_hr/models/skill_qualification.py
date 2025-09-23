from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date

# Classe Recrutement
class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    techskill_ids = fields.One2many(
        "emp.tech.skills", "applicant_id", "Technical Skills"
    )
    nontechskill_ids = fields.One2many(
        "emp.nontech.skills", "applicant_id", "Non-Technical Skills"
    )
    education_ids = fields.One2many("employee.education", "applicant_id", "Education")
    certification_ids = fields.One2many(
        "employee.certification", "applicant_id", "Certification"
    )
    profession_ids = fields.One2many(
        "employee.profession", "applicant_id", "Professional Experience"
    )

    def create_employee_from_applicant(self):
        """Create an hr.employee from the hr.applicants"""
        res = super(HrApplicant, self).create_employee_from_applicant()
        for applicant in self:
            res["context"].update(
                {
                    "default_techskill_ids": [(6, 0, applicant.techskill_ids.ids)],
                    "default_nontechskill_ids": [
                        (6, 0, applicant.nontechskill_ids.ids)
                    ],
                    "default_education_ids": [(6, 0, applicant.education_ids.ids)],
                    "default_certification_ids": [
                        (6, 0, applicant.certification_ids.ids)
                    ],
                    "default_profession_ids": [(6, 0, applicant.profession_ids.ids)],
                }
            )
        return res

# Classe Qualification

class EmployeeEducation(models.Model):
    _name = "employee.education"
    _description = "Employee Education"

    applicant_id = fields.Many2one("hr.applicant", "Candidat")
    employee_id = fields.Many2one("hr.employee", "Employé")
    type_id = fields.Many2one("hr.recruitment.degree", "Diplôme", ondelete="cascade")
    institute_id = fields.Many2one("hr.institute", "Institutes", ondelete="cascade")
    score = fields.Char()
    qualified_year = fields.Date()
    doc = fields.Binary("Pièce Jointe")


class HrInstitute(models.Model):
    _name = "hr.institute"
    _description = "Hr Institute"

    name = fields.Char()
    country_id = fields.Many2one("res.country", "Pays")
    state_id = fields.Many2one("res.country.state", "Ville")


class EmployeeCertification(models.Model):
    _name = "employee.certification"
    _description = "Employee Certification"

    applicant_id = fields.Many2one("hr.applicant", "Candidat")
    employee_id = fields.Many2one("hr.employee", "Employé")
    course_id = fields.Many2one("cert.cert", "Formation", ondelete="cascade")
    levels = fields.Char("Niveaux d'achèvement")
    year = fields.Date("Année de Réalisation")
    doc = fields.Binary("Certificats")


class CertCert(models.Model):
    _name = "cert.cert"
    _description = "Cert Cert"

    name = fields.Char("Formation")


class EmployeeProfession(models.Model):
    _name = "employee.profession"
    _description = "Employee Profession"

    applicant_id = fields.Many2one("hr.applicant", "Candidat")
    employee_id = fields.Many2one("hr.employee", "Employé")
    job_id = fields.Many2one("hr.job", "Poste")
    location = fields.Char()
    from_date = fields.Date("Date Début")
    to_date = fields.Date("Date Fin")
    doc = fields.Binary("Certificats d'Expérience")

    _sql_constraints = [
        (
            "to_date_greater",
            "check(to_date > from_date)",
            "La date de début de l'expérience professionnelle doit être inférieure à la date de fin !",
        ),
    ]

    @api.constrains("from_date", "to_date")
    def check_from_date(self):
        """
        This method is called when future Start date is entered.
        --------------------------------------------------------
        @param self : object pointer
        """
        today = date.today()
        if (self.from_date > today) or (self.to_date > today):
            raise ValidationError(
                "La future date de début ou la date de fin de l'expérience professionnelle n'est pas acceptable !!"
            )

# Classe Skill

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    techskill_ids = fields.One2many(
        "emp.tech.skills", "employee_id", "Compétences Techniques"
    )
    nontechskill_ids = fields.One2many(
        "emp.nontech.skills", "employee_id", "Soft Skills"
    )
    education_ids = fields.One2many("employee.education", "employee_id", "Education")
    certification_ids = fields.One2many(
        "employee.certification", "employee_id", "Certification"
    )
    profession_ids = fields.One2many(
        "employee.profession", "employee_id", "Expérience Professionnelle"
    )


class EmployeeTechSkills(models.Model):
    _name = "emp.tech.skills"
    _description = "Employee Tech Skills"

    applicant_id = fields.Many2one("hr.applicant", "Candidat")
    employee_id = fields.Many2one("hr.employee", "Employé")
    tech_id = fields.Many2one("tech.tech", "Compétences Techniques", ondelete="cascade")
    levels = fields.Selection(
        [("basic", "Basique"), ("medium", "Moyen"), ("advance", "Avancé")], "Niveaux"
    )


class TechTech(models.Model):
    _name = "tech.tech"
    _description = "Tech Tech"

    name = fields.Char()

    def unlink(self):
        """
        This method is called user tries to delete a skill which
        is already in use by an employee.
        --------------------------------------------------------
        @param self : object pointer
        """
        tech_skill = self.env["emp.tech.skills"].search([("tech_id", "in", self.ids)])
        print(tech_skill)
        if tech_skill:
            raise UserError(
                _(
                    "Vous essayez de supprimer une compétence qui est référencée par un employé."
                )
            )
        return super(TechTech, self).unlink()


class EmployeeNonTechSkills(models.Model):
    _name = "emp.nontech.skills"
    _description = "Employee Non Tech Skills"

    applicant_id = fields.Many2one("hr.applicant", "Candidat")
    employee_id = fields.Many2one("hr.employee", "Employé")
    nontech_id = fields.Many2one(
        "nontech.nontech", "Soft Skills", ondelete="cascade"
    )
    levels = fields.Selection(
        [("basic", "Basique"), ("medium", "Moyen"), ("advance", "Avancé")], "Niveaux"
    )


class NontechNontech(models.Model):
    _name = "nontech.nontech"
    _description = "Nontech Nontech"

    name = fields.Char()

    def unlink(self):
        """
        This method is called user tries to delete a skill which
        is already in use by an employee.
        --------------------------------------------------------
        @param self : object pointer
        """
        tech_skill = self.env["emp.nontech.skills"].search(
            [("nontech_id", "in", self.ids)]
        )
        if tech_skill:
            raise UserError(
                _(
                    "Vous essayez de supprimer une compétence qui est référencée par un employé."
                )
            )
        return super(NontechNontech, self).unlink()

