from odoo import fields, models, api, _





class ReportLoan(models.AbstractModel):
    _name = 'report.nn_loan.report_loan_template'
    _description = 'Rapport des prets'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.loan'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.loan',
            'docs': docs,
            'data': data,
        }