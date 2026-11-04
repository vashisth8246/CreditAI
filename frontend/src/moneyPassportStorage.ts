import { readPassports, today } from './moneyChallenge'

export function loadSaved() {
  try {
    return { passports: readPassports(localStorage, today()), error: '' }
  } catch {
    return { passports: [], error: 'Saved passports could not be opened. Export any active passport before clearing browser data.' }
  }
}
