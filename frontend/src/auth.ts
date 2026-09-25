export type AuthResponse={access_token:string;token_type?:string;user?:unknown};

/** The single session entry point used by registration and normal login. */
export function establishSession(response:AuthResponse):string{
 if(!response?.access_token)throw new Error('Authentication succeeded without an access token. Please try again.');
 localStorage.setItem('token',response.access_token);
 return response.access_token;
}

export function destinationAfterAuthentication(isRegistration:boolean):string{
 return isRegistration?'/onboarding':'/dashboard';
}
