export type ResearchFieldPresentation = {
  title: string
  group: 'Borrower profile' | 'Repayment status' | 'Bill statements' | 'Previous payments'
}

/** Display names stay centralized; descriptions and category labels come from the live backend schema. */
export const RESEARCH_FIELD_PRESENTATION: Record<string, ResearchFieldPresentation> = {
  LIMIT_BAL: { title: 'Credit limit', group: 'Borrower profile' },
  SEX: { title: 'Gender code', group: 'Borrower profile' },
  EDUCATION: { title: 'Education code', group: 'Borrower profile' },
  MARRIAGE: { title: 'Marital status code', group: 'Borrower profile' },
  AGE: { title: 'Age', group: 'Borrower profile' },
  PAY_0: { title: 'Repayment status · September 2005', group: 'Repayment status' },
  PAY_2: { title: 'Repayment status · August 2005', group: 'Repayment status' },
  PAY_3: { title: 'Repayment status · July 2005', group: 'Repayment status' },
  PAY_4: { title: 'Repayment status · June 2005', group: 'Repayment status' },
  PAY_5: { title: 'Repayment status · May 2005', group: 'Repayment status' },
  PAY_6: { title: 'Repayment status · April 2005', group: 'Repayment status' },
  BILL_AMT1: { title: 'Bill statement · September 2005', group: 'Bill statements' },
  BILL_AMT2: { title: 'Bill statement · August 2005', group: 'Bill statements' },
  BILL_AMT3: { title: 'Bill statement · July 2005', group: 'Bill statements' },
  BILL_AMT4: { title: 'Bill statement · June 2005', group: 'Bill statements' },
  BILL_AMT5: { title: 'Bill statement · May 2005', group: 'Bill statements' },
  BILL_AMT6: { title: 'Bill statement · April 2005', group: 'Bill statements' },
  PAY_AMT1: { title: 'Previous payment · September 2005', group: 'Previous payments' },
  PAY_AMT2: { title: 'Previous payment · August 2005', group: 'Previous payments' },
  PAY_AMT3: { title: 'Previous payment · July 2005', group: 'Previous payments' },
  PAY_AMT4: { title: 'Previous payment · June 2005', group: 'Previous payments' },
  PAY_AMT5: { title: 'Previous payment · May 2005', group: 'Previous payments' },
  PAY_AMT6: { title: 'Previous payment · April 2005', group: 'Previous payments' },
}

export function researchFieldTitle(name: string): string {
  return RESEARCH_FIELD_PRESENTATION[name]?.title ?? name
}

export function researchFieldGroup(name: string): ResearchFieldPresentation['group'] {
  return RESEARCH_FIELD_PRESENTATION[name]?.group ?? 'Borrower profile'
}
