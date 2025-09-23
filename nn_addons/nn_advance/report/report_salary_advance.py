from odoo import fields, models, api, _

class ReportSalaryAdvance(models.AbstractModel):
    _name = 'report.nn_advance.report_salary_advance_template'
    _description = 'Rapport d\'avance sur salaire'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['salary.advance'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'salary.advance',
            'docs': docs,
            'data': data,
        }