import re
from email_validator import validate_email, EmailNotValidError
import dns.resolver
from core.common_email_typos import COMMON_DOMAIN_TYPOS

class EmailValidator:
    """
    Email validation and correction class
    """
    
    def __init__(self):
        self.common_domain_typos = COMMON_DOMAIN_TYPOS
    
    def validate_and_correct(self, email):
        """
        Validate and attempt to correct an email address
        
        Returns:
            dict: {
                'status': 'valid' | 'corrected' | 'invalid',
                'corrected_email': str (if corrected),
                'reason': str
            }
        """
        if not email or pd.isna(email):
            return {
                'status': 'invalid',
                'reason': 'Empty or null email'
            }
        
        email = str(email).strip().lower()
        
        # Check for basic syntax issues that can be corrected
        corrected_email = self.attempt_correction(email)
        
        if corrected_email != email:
            # Try validating the corrected version
            validation_result = self.validate_email_syntax(corrected_email)
            if validation_result['valid']:
                return {
                    'status': 'corrected',
                    'corrected_email': corrected_email,
                    'reason': 'Corrected common typo or formatting issue'
                }
        
        # Validate the original or corrected email
        validation_result = self.validate_email_syntax(email if corrected_email == email else corrected_email)
        
        if validation_result['valid']:
            # Check if domain has MX records
            domain_check = self.check_domain(validation_result['domain'])
            
            if domain_check['valid']:
                return {
                    'status': 'valid',
                    'reason': 'Valid email with existing domain'
                }
            else:
                return {
                    'status': 'invalid',
                    'reason': f"Domain issue: {domain_check['reason']}"
                }
        else:
            return {
                'status': 'invalid',
                'reason': validation_result['reason']
            }
    
    def attempt_correction(self, email):
        """
        Attempt to correct common email typos
        """
        # Remove extra spaces
        email = email.replace(' ', '')
        
        # Fix multiple @ symbols (keep only the last one)
        if email.count('@') > 1:
            parts = email.split('@')
            email = parts[0] + '@' + parts[-1]
        
        # Check for missing @ symbol but has a dot
        if '@' not in email and '.' in email:
            # Try to guess where @ should be
            parts = email.split('.')
            if len(parts) >= 2:
                # Assume format like: username.domain.com -> username@domain.com
                email = parts[0] + '@' + '.'.join(parts[1:])
        
        # Split email into local and domain parts
        if '@' in email:
            local, domain = email.rsplit('@', 1)
            
            # Check for common domain typos
            if domain in self.common_domain_typos:
                domain = self.common_domain_typos[domain]
                email = f"{local}@{domain}"
            
            # Fix double dots
            domain = re.sub(r'\.{2,}', '.', domain)
            local = re.sub(r'\.{2,}', '.', local)
            
            email = f"{local}@{domain}"
        
        return email
    
    def validate_email_syntax(self, email):
        """
        Validate email syntax using email-validator library
        """
        try:
            validated = validate_email(email, check_deliverability=False)
            return {
                'valid': True,
                'email': validated.normalized,
                'domain': validated.domain
            }
        except EmailNotValidError as e:
            return {
                'valid': False,
                'reason': str(e)
            }
    
    def check_domain(self, domain):
        """
        Check if domain has valid MX records
        """
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if mx_records:
                return {
                    'valid': True,
                    'reason': 'Domain has valid MX records'
                }
            else:
                return {
                    'valid': False,
                    'reason': 'No MX records found'
                }
        except dns.resolver.NXDOMAIN:
            return {
                'valid': False,
                'reason': 'Domain does not exist'
            }
        except dns.resolver.NoAnswer:
            return {
                'valid': False,
                'reason': 'No MX records found'
            }
        except dns.resolver.Timeout:
            return {
                'valid': False,
                'reason': 'DNS lookup timeout'
            }
        except Exception as e:
            return {
                'valid': False,
                'reason': f'DNS error: {str(e)}'
            }


# Import pandas for the validator
import pandas as pd