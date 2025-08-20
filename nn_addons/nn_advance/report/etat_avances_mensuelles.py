from odoo import models
from datetime import datetime

class EtatAvancesMensuellesXlsx(models.AbstractModel):
    _name = 'report.nn_advance.etat_avances_mensuelles'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Etat Avances Mensuelles XLSX Report'


    def generate_xlsx_report(self, workbook, data, etat_avances_mensuelles):
        try:
            for etat_avances_mensuelles in etat_avances_mensuelles:
                if not etat_avances_mensuelles:
                    raise ValueError("Aucun enregistrement trouvé")

                report_name = "Avances Mensuelles"
                if hasattr(etat_avances_mensuelles, 'name') and etat_avances_mensuelles.name:
                    report_name = f"Avances Mensuelles {etat_avances_mensuelles.name}"
                sheet = workbook.add_worksheet(report_name[:31])

                # Define formats
                bold = workbook.add_format({'bold': True, 'align': 'center'})
                title_format = workbook.add_format({
                    'bold': True,
                    'align': 'center',
                    'font_size': 16,
                    'font_color': 'black',
                    'border': 0
                })
                header_info_format = workbook.add_format({
                    'bold': True,
                    'align': 'left',
                    'font_size': 11
                })
                header_format = workbook.add_format({
                    'bold': True,
                    'align': 'center',
                    'border': 1,
                    'bg_color': '#DDDDDD'
                })
                default_format = workbook.add_format({
                    'align': 'left',
                    'border': 1
                })
                amount_format = workbook.add_format({
                    'align': 'right',
                    'border': 1,
                    'num_format': '#,##0.000'
                })
                date_format = workbook.add_format({
                    'align': 'center',
                    'border': 1,
                    'num_format': 'dd/mm/yyyy'
                })

                # Set column widths
                sheet.set_column(0, 0, 15)  # Matricule
                sheet.set_column(1, 1, 25)  # Nom et Prénom
                sheet.set_column(2, 2, 20)  # Departement
                sheet.set_column(3, 3, 15)  # Date d'avance
                sheet.set_column(4, 4, 15)  # Montant Avance
                sheet.set_column(5, 5, 15)  # Date de retenu
                sheet.set_column(6, 6, 15)  # Payé

                # Add title
                sheet.merge_range('A1:G2', 'État des Avances Mensuelles', title_format)

                # Add header information
                sheet.write(3, 0, 'Période:', header_info_format)
                mois = getattr(etat_avances_mensuelles, 'mois', '') or ''
                sheet.write(3, 1, mois, default_format)

                sheet.write(4, 0, 'Date d\'édition:', header_info_format)
                sheet.write(4, 1, datetime.now().strftime('%d/%m/%Y'), default_format)

                # Add headers
                current_row = 7
                headers = [
                    "Matricule",
                    "Nom et Prénom",
                    "Departement",
                    "Date d'avance",
                    "Montant Avance",
                    "Date de retenu",
                    "Payé"
                ]

                for col, header in enumerate(headers):
                    sheet.write(current_row, col, header, header_format)

                # Add data rows
                row = current_row + 1
                total_amount = 0

                if hasattr(etat_avances_mensuelles, 'journal_avances_line_ids'):
                    for line in etat_avances_mensuelles.journal_avances_line_ids:
                        matricule = getattr(line, 'matricule', '') or ''
                        employe_name = line.employe_id.name if hasattr(line, 'employe_id') and line.employe_id else ''
                        department = getattr(line, 'department', '') or ''
                        description_amount = getattr(line, 'description_amount', 0.000) or 0.000
                        paye = getattr(line, 'paye', False)

                        sheet.write(row, 0, matricule, default_format)
                        sheet.write(row, 1, employe_name, default_format)
                        sheet.write(row, 2, department, default_format)

                        # Write dates with proper formatting
                        if hasattr(line, 'date_avance') and line.date_avance:
                            sheet.write(row, 3, line.date_avance, date_format)
                        else:
                            sheet.write(row, 3, '', default_format)

                        # Write amount with format
                        sheet.write(row, 4, description_amount, amount_format)
                        # sheet.write_rich_string(row, 4, amount_format, f'{description_amount:,.3f}', default_format,
                        #                         " DT")

                        # Write date_retenu with proper formatting
                        if hasattr(line, 'date_retenu') and line.date_retenu:
                            sheet.write(row, 5, line.date_retenu, date_format)
                        else:
                            sheet.write(row, 5, '', default_format)

                        sheet.write(row, 6, "Payé" if paye else "En Attente", default_format)

                        total_amount += description_amount
                        row += 1

                # Add total row
                sheet.write(row, 3, "Total", bold)
                sheet.write(row, 4, total_amount, amount_format)
                # sheet.write_rich_string(row, 4, amount_format, f'{total_amount:,.3f}', default_format, " DT")

        except Exception as e:
            error_sheet = workbook.add_worksheet('Erreur')
            error_sheet.write(0, 0, f"Une erreur s'est produite: {str(e)}")
            raise