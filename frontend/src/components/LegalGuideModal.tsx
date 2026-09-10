import React from 'react';
import { BookOpen, Scale, ShieldAlert } from 'lucide-react';

export const LegalGuideModal: React.FC = () => {
  const rules = [
    {
      rule: 'Rule 6(1)(a) & (ab)',
      title: 'Name & Address of Manufacturer / Packer / Importer',
      desc: 'Every packaged commodity must state the complete name and registered address of the manufacturer. Where the manufacturer is not the packer, both name and address must be stated. In case of imported goods, the name and address of the importer must be declared.',
      punishment: 'Non-declaration constitutes an offense punishable under Section 36 of the Legal Metrology Act, 2009.',
    },
    {
      rule: 'Rule 6(1)(b)',
      title: 'Generic / Common Name of Commodity',
      desc: 'The common or generic name of the commodity contained in the package must be prominently declared on the principal display panel so consumers are not misled about the nature of the contents.',
      punishment: 'Misleading or omitted generic name attracts fines up to ₹25,000 for first offense.',
    },
    {
      rule: 'Rule 6(1)(c) & Rule 11',
      title: 'Net Quantity in Standard SI Units',
      desc: 'Declaration of net quantity must use standard SI units (g, kg, ml, l, m, cm) or number (N / U). Using non-standard symbols like "gms", "kilos", or "ltrs" is strictly prohibited under Rule 11.',
      punishment: 'Sale of non-standard units triggers package seizure and penalty under Rule 32.',
    },
    {
      rule: 'Rule 6(1)(d)',
      title: 'Month & Year of Manufacture / Packing / Import',
      desc: 'Every package must bear the month and year in which it was manufactured, pre-packed, or imported. It should be formatted in standard digits or abbreviated month (e.g. 08/2026 or Aug 2026).',
      punishment: 'Failure to declare manufacturing date prevents batch tracking and invites statutory notice.',
    },
    {
      rule: 'Rule 6(1)(e)',
      title: 'Maximum Retail Price (MRP) & Tax Inclusivity',
      desc: 'The retail sale price must be declared in Indian currency as "MRP Rs. XX.XX" or "MRP ₹ XX.XX", and must explicitly state the mandatory phrase "inclusive of all taxes" or "incl. of all taxes".',
      punishment: 'Charging above MRP or omitting tax phrasing is a cognizable violation under the Act.',
    },
    {
      rule: 'Rule 6(1)(f)',
      title: 'Best Before or Expiry Date (Perishables)',
      desc: 'Mandatory for all commodities that may become unfit for human consumption after a period of time. Must state "Best before X months from packaging" or an explicit expiry date.',
      punishment: 'Harmonized with FSSAI regulations; critical consumer safety mandate.',
    },
    {
      rule: 'Rule 6(1)(g)',
      title: 'Consumer Care / Grievance Redressal Mechanism',
      desc: 'Mandates the name, address, telephone number, and email address of the person/office who can be contacted by the consumer in case of queries, defects, or complaints.',
      punishment: 'Absence of consumer grievance channels directly violates the Consumer Protection Act.',
    },
    {
      rule: 'Rule 6(1)(n) (2017 Amend.)',
      title: 'Country of Origin (Imported Products)',
      desc: 'For any imported package, the name of the country of origin or manufacture or assembly must be clearly displayed on the package.',
      punishment: 'Customs clearance detention and regulatory enforcement by Metrology inspectors.',
    },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs space-y-6">
      {/* Header */}
      <div className="border-b border-slate-100 pb-5">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-700">
            <Scale className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">
              India's Legal Metrology (Packaged Commodities) Rules, 2011
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Statutory declaration guidelines mandated under the Ministry of Consumer Affairs, Food & Public Distribution.
            </p>
          </div>
        </div>
      </div>

      {/* Overview Card */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-sky-50 to-indigo-50 border border-sky-100 text-xs text-slate-700 space-y-2">
        <div className="flex items-center space-x-2 font-bold text-sky-900">
          <BookOpen className="w-4 h-4 text-sky-700" />
          <span>Purpose of LabelCheck Compliance Engine</span>
        </div>
        <p className="leading-relaxed">
          The Legal Metrology (Packaged Commodities) Rules, 2011 require all pre-packaged commodities sold in India
          to carry clear, non-deceptive mandatory declarations on the principal display panel. Non-compliance results in
          seizure of goods and compounding fees under Section 36 of the Legal Metrology Act, 2009. LabelCheck provides automated
          pre-shipment and pre-market audit verification for manufacturers, brand owners, and regulatory inspectors.
        </p>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rules.map((r, idx) => (
          <div key={idx} className="p-4 rounded-xl border border-slate-200 hover:border-sky-300 transition-colors bg-slate-50/50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-sky-100 text-sky-800">
                {r.rule}
              </span>
              <span className="text-[11px] font-semibold text-slate-400">Rule #{idx + 1}</span>
            </div>
            <h4 className="text-sm font-bold text-slate-900">{r.title}</h4>
            <p className="text-xs text-slate-600 leading-relaxed">{r.desc}</p>
            <div className="pt-2 border-t border-slate-200/60 flex items-start space-x-1.5 text-[11px] text-rose-700">
              <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>{r.punishment}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
