import {z} from 'zod';

export const emailSchema=z.string().trim().email('Enter a valid email address.');

export type EmailValidationState='untouched'|'empty'|'valid'|'invalid';

export function emailValidationState(value:string,interacted:boolean):EmailValidationState{
 if(!interacted&&!value)return 'untouched';
 if(!value.trim())return 'empty';
 return emailSchema.safeParse(value).success?'valid':'invalid';
}

/** Trim surrounding whitespace and normalize only the case-insensitive domain. */
export function normalizeEmail(value:string):string{
 const trimmed=value.trim();
 const at=trimmed.lastIndexOf('@');
 return at<0?trimmed:`${trimmed.slice(0,at)}@${trimmed.slice(at+1).toLowerCase()}`;
}
