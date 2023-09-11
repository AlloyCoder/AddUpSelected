"""
Program: AddupSelected.py
Author: AlloyCoder (with GPT-4 assistance)
Version: 1.05
Release Date: 9/11/2023
License: The Unlicense (Unrestricted public domain)
Python Version: 2.7.18 - Developed using Notepad++ v8.5.6

Purpose:
    This script serves as a plug-in for the Notepad++ editor, designed to sum up numbers within a selected text range.
    It aims to provide an intuitive utility for everyday use, focusing on common decimal notation, negative numbers,
    dollar amounts, and proper comma-separated thousands-grouping. Scientific notation is intentionally ignored.
    Anything reminiscent of arithmetic will be ignored and not counted.  Lots of other characters like () [] I consider neutral and valid. And yes this is highly subjective. 
    
Usage:
    Upon successful execution, a pop-up window displays the total sum.
    The sum is always copied to the clipboard as "Selected Sum = 100.00".
    Additional pop-up notifications appear if negative numbers or numbers with too many digits were encountered in the selection.
    

Features:
    - Supports arbitrary precision up to 60 decimal places (set it with getcontext().prec= )
    - Recognizes only the period (".") as the decimal separator.
    - Handles negative numbers and optional dollar signs.
    - Filters out numbers with ambiguous formatting or characters.
    - Multiple negative signs invalidate a number.  We're not doing arithmetic, just removing plausibly neutral characters from numbers,
       like [], (), $, trailing *, etc. See examples below.  
       Trailing asterisks are assumed to be neutral footnote markers, not multiplication signs. 
       

Notes:
    Inspired by the TextFX number add-up plugin, of which no 64-bit version exists yet for Notepad++.
"""

# Test examples: 
#
#            7.     " -$10.00,  "   +$700.-----  ,   (00.100),    $1,000,000.-- ,   "199.99*",  "1"   and   -$$9;      " [-$400.0-;]      [-[$600*]*]    +++[[500]],   [[100.----------------*]*],   "      I consider these valid numbers.  
#
#  Test: total numbers of above line should be:  Selected Sum = 1000489.09      +-40    
#
#             7    -10 700 0.1 1000000  199.99 1  -9 -400 -600 500 100  40
#           
#  Numbers below are too ambiguous, e.g. could be intended as calculations, IP addresses, etc. 
#
#       ~3172      "9(99)"    10,0.123  ,   2008-10-09,   ,  "   $48.00/year  " ,   70,00,00.00    -[-[40]]   7*7    11?   46.58%     1.1.0.168    5x   10-1     ]7[   *9     
#
#


from Npp import *
from decimal import Decimal, getcontext, InvalidOperation, localcontext
import subprocess
import re
import time
import string 

MAX_PRECISIONDIGITS = 60
DO_PROFILING = True 

# Pre-compiled regular expression for number matching
COMMA_NUM_RE = re.compile(r"^\d{1,3}(,\d{3})*(\.\d+)?$")  #  match numbers that are formatted with commas as thousand separators and a period as the decimal separator. 
NON_NUMERIC_RE = re.compile(r"[^\d]")  # match anything not a digit. 
INVALID_CHAR_RE = re.compile(r"[a-df-zA-DF-Z]")   # match anything that's alphabetic except e, E (exponent in scientific notation)
ANY_ALPHA_RE = re.compile(r"[a-zA-Z]")   # match anything that's alphabetic. 
ANY_LOWERALPHA_RE = re.compile(r"[a-z]")   # match anything that's lowercase letter. 

ANY_DISQUALIFIER_RE = re.compile(r"[!#%&:<>?@_|\^\\\/]")  #match anything that's a subjectrively disqualifying character.

DIGIT_RE = re.compile(r'[0-9]')    # Match anything that is a decimal digit. 

STRIPPABLE_CHAR_RE = re.compile(r"[\$\(\)\*\+\,\-\'\"\;\[\]]")    # Potentially valid, neutral characters: semicolon, comma, dollar sign, parentheses, brackets, plus, minus, asterisk, single and double quotes. 



#Pre create decimal objects
ZERO_DECIMAL = Decimal('0.0')

# Global counters 
skipped_due_to_precision = 0
conversion_fail_count = 0    

#Note - these can be recognized by the arbitrary precision Decimal library. Since we exclude all letters we don't need check for these.
# special_strings = {"infinity", "-infinity", "+infinity", "nan", "snan", "inf", "-inf"}

# Check if any alphanumeric characters are in a string. 
def has_unicode_char(s):
    return any(c.isalpha() for c in s)
    

# Copy text to clipboard
def copy_to_clipboard(text):
    CREATE_NO_WINDOW = 0x08000000
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    subprocess.Popen(['clip'], stdin=subprocess.PIPE, startupinfo=startupinfo).communicate(text.encode('utf-8'))



def parse_number(num_str) :
    """
    Validates and parses a given number string and returns a Decimal object.
    
    :param str num_str: The number string to parse.
    :return: Parsed Decimal object, or None if invalid.
    :rtype: Decimal or None
    """
        
    global skipped_due_to_precision
    global conversion_fail_count
            
    sign = 1
    minus_count = 0 
    
    # Pre-check if any stripping or processing of valid characters is needed. 
    # Peel potentially nested [] and () around a number, leading +, and trailing * asterisks, then count up all valid minus signs encountered. 
    if STRIPPABLE_CHAR_RE.search(num_str):
        prev_length = -1
        while len(num_str) != prev_length:
            prev_length = len(num_str)
            num_str = num_str.rstrip('])*;,').lstrip('+$([').strip("\'\"")  # strip *,],);,, from right, $,+,(,[ from left, and  ' and " from around a number.                
            if num_str.startswith('-'):  
                num_str = num_str[1:]  # Remove a leading '-' and note it as a minus.                 
                minus_count += 1        # log the - occurrence.
                                                    
        # Handle negative numbers 
        if minus_count == 1: 
            sign = -1        
        elif minus_count > 1:    # multiple negation creates an invalid/ambiguous number; we're not doing arithmetic, just removing plausibly neutral characters from numbers.
            return None             # there may still be minuses (dashes) embedded in numbers. The final Decimal()  digestion will catch those.             
    
            
    
    #  Handle decimal points and any trailing dashes which possibly signifyi zeroes after the decimal point.
    #   Very specific.  100--  is seen as too ambiguous,  but 23.--   and  100.0--  and 555.   are valid.  
    decimaldot_count = num_str.count('.')    
    
    # Trailing dashes signify zeroes if there is a decimal point. Multiple decimal points are disqualifying, but Decimal() conversion should take care of that. 
    if(decimaldot_count == 0  and num_str.endswith('-')) or (decimaldot_count > 1):
        return None #  Invalid number e.g. " 17-  or   1.1.1.1 "
    
    if (decimaldot_count == 1 and num_str.endswith('-')):
        num_str = num_str.rstrip('-')  + "0"   # Numbers like 7.-- become 7.0 
            
    # Validate proper thousands separators. 
    if "," in num_str:
        if not COMMA_NUM_RE.match(num_str):   
            return None                                
        num_str = num_str.replace(",", "")   # We have to remove even proper separator commas because Decimal doesn't allow them. 
        
    # Check if the total length might exceed our precision capability.
    if len(num_str) >= MAX_PRECISIONDIGITS:
        skipped_due_to_precision += 1  
        return None
        
    # Final conversion. We handled the sign ourselves.
    try:
        return sign * Decimal(num_str)
    except InvalidOperation:
        conversion_fail_count += 1
        #print("Failed to convert: {}".format(num_str))   # Extra logging. Development only. 
        return None




# Main code 

with localcontext() as ctx:

    ctx.prec = MAX_PRECISIONDIGITS
    if DO_PROFILING:
        start_time = time.time()     #  For profiling purposes.
    line_count = 0         
    validnumbers_count = 0
    grand_total = ZERO_DECIMAL
    negative_numbers_count = 0
    
    get_selections = editor.getSelections()
    
    for sel in range(get_selections):
        start_pos = editor.getSelectionNStart(sel)
        end_pos = editor.getSelectionNEnd(sel)
        text = editor.getTextRange(start_pos, end_pos).strip()
        lines = text.split('\n')
        
        for line in lines:
            line_count  += 1                        
            line_tokens = line.split()
            
            for num_string in line_tokens:            
            
                # Evaluate the string.                                 
                if not DIGIT_RE.search(num_string):         # Skip this string as it contains no decimal digits.   
                    continue
                if ANY_ALPHA_RE.search(num_string):       # Skip this string as it contains any letters of the alphabet. Won't be a simple unambiguous number. 
                    continue                                      
                if ANY_DISQUALIFIER_RE.search(num_string):    # Ignore all numbers with additional disqualifying ambiguous characters.
                    continue     
                    
                parsed_num = parse_number(num_string)   # The real work. Returns a Decimal type (arbitrary precision.)                
                                
                if parsed_num is  None:
                    #print("Failed to convert: [{}]".format(num_string))    #LOGGING 
                    continue 
                    
                validnumbers_count += 1
                    
                if parsed_num < 0:
                    negative_numbers_count += 1                
                
                # Finally add the number we found and digested. There is a theoretical possibility for overflow 
                # as sometimes too many borderline large numbers are accepted and added.
                grand_total += parsed_num           # Addition, in Decimal type format. 
                
                
                
    # Ready to display the results.
    if validnumbers_count > 0:
        if grand_total % 1 == 0:
            sum_resultstring = 'Selected Sum = {}'.format(int(grand_total))
        else:
            rounded_grand_total = grand_total.quantize(Decimal('0.00'))
            if rounded_grand_total == grand_total:
                sum_resultstring = 'Selected Sum = {:.2f}'.format(grand_total)
            else:
                sum_resultstring = 'Selected Sum = {}'.format(grand_total)
    else: 
        sum_resultstring = 'No selected valid numbers were found.'
                
    if DO_PROFILING:
        elapsed_time = (time.time() - start_time) * 1000   # Convert to milliseconds. For profiling purposes.     
    
    copy_to_clipboard(sum_resultstring)
        
    if validnumbers_count > 0:
        message = sum_resultstring + '\nIn all, {} numbers were evaluated and added.'.format(validnumbers_count)    
        if negative_numbers_count > 0:
            message += ' \nOf those, {} were negative numbers.'.format(negative_numbers_count)        
        notepad.messageBox(message) 
         
    if skipped_due_to_precision > 0:
        notepad.messageBox('{} numbers ignored due to digit length exceeding {}'.format(skipped_due_to_precision, ctx.prec), '')
    
    # Display elapsed time.  For profiling purposes.
    if DO_PROFILING:
        notepad.messageBox("Elapsed Time: {:.2f} ms".format(elapsed_time), "Performance Metrics")      
        print("Elapsed Time: {:.2f} ms".format(elapsed_time))    # Extra logging. Development only.      
    
    
#    if conversion_fail_count > 0:
#        notepad.messageBox('{} numbers ignored due to conversion errors to arbitrary precision Decimal format.'.format(conversion_fail_count)) 
                
#    print(" {} numbers ignored due to conversion errors to Decimal arbitrary precision library format.".format(conversion_fail_count))     # Extra logging. Development only. 
    
