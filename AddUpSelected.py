"""
Program: AddupSelected.py
Author: AlloyCoder (with GPT-4 assistance)
Version: 1.04
Release Date: 9/09/2023
License: The Unlicense (Unrestricted public domain)
Python Version: 2.7.18 (Notepad++)

Purpose:
    This script serves as a plug-in for the Notepad++ editor, designed to sum up numbers within a selected text range.
    It aims to provide a simple and intuitive utility for everyday use, focusing on decimal notation, negative numbers,
    dollar amounts, and proper comma-separated thousands-grouping. Scientific notation is intentionally ignored.
    Anything reminiscent of arithmetic will be ignored and not counted.  Lots of other characters like () [] I consider neutral and valid. And yes this is highly subjective. 

Features:
    - Supports arbitrary precision up to 60 decimal places (set it with getcontext().prec= )
    - Recognizes only the period (".") as the decimal separator.
    - Handles negative numbers and optional dollar signs.
    - Filters out numbers with ambiguous formatting or characters.
    - Multiple negative signs invalidate a number.  We're not doing arithmetic, just removing plausibly neutral characters from numbers,
       like [], (), $, trailing *, etc. See examples below.  
       Trailing asterisks are assumed to be neutral footnote markers, not multiplication signs. 
       
       

Usage:
    Upon successful execution, a pop-up window displays the total sum.
    The sum is also copied to the clipboard in the format: "Selected Sum = 100".
    Additional pop-up notifications appear if negative numbers or numbers with too many digits were encountered in the selection.

Notes:
    Inspired by the TextFX number add-up plugin, which was never ported to the 64-bit version of Notepad++.
"""

#
# Test examples: 
#
#            7.     " -$10.00,  "   +$700.-----  ,   (00.100),    $1,000,000.-- ,   "199.99*",  "1"   and   -$$9      " [-$400.00]      [-[$600*]*]    +++[[500]],   [[100*]*],   "      I consider these valid numbers.  
#
#  Test: total numbers of above line should be:  Selected Sum = 1000489.09
#
#                1,00.123  ,   2008-10-09,   ,  "   $48.00/year  " ,   70,00,00.00    -[-[40]]   7*7    11?   46.58%     1.1.0.168    5x   10-1     ]7[   *9     etc.  are ambiguous, or could be calculations.  This line should sum to zero/none. 
#

from Npp import *
from decimal import Decimal, getcontext, InvalidOperation, localcontext
import subprocess
import re
import time
import string 

MAX_PRECISION = 60
DO_PROFILING = False 

# Pre-compiled regular expression for number matching
COMMA_NUM_RE = re.compile(r"^\d{1,3}(,\d{3})*(\.\d+)?$")    #  match numbers that are formatted with commas as thousand separators and a period as the decimal separator. 
NON_NUMERIC_RE = re.compile(r"[^\d]")                   #match anything not a digit. 
INVALID_CHAR_RE = re.compile(r"[a-df-zA-DF-Z]")   #match anything that's alphabetic except e, E (exponent in scientific notation)
ANY_ALPHA_RE = re.compile(r"[a-zA-Z]")   #match anything that's alphabetic. 

ANY_DISQUALIFIER_RE = re.compile(r"[!#%&:;<>?@_|\^\\\/]")  #match anything that's a subjectrively disqualifying character like  ?, !, %, : (colon)  & (ampersand) # (pound) <> (smaller/greaterthan) ^ caret \ backslash | pipe  

DIGIT_RE = re.compile(r'[0-9]')    #match anythign that is a digit. 

VALID_CHAR_RE = re.compile(r'[\$\(\)\*\+\-\[\]]')   #potentiall valid, neutral characters.




#Pre create decimal objects
ZERO_DECIMAL = Decimal('0.0')

# Global counters 
skipped_due_to_precision = 0
# conversion_fail_count = 0    

#these can be recognized by the arbitrary precision Decimal library.
special_strings = {"infinity", "-infinity", "+infinity", "nan", "snan", "inf", "-inf"}


# Try the 'string' library...
def has_alphabetic_char(s):
    return any(c in string.ascii_letters for c in s)

    
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


# Validate and parse numbers.  type: (str) -> Decimal 
def parse_number(num_str) :
        
    global skipped_due_to_precision
    #global conversion_fail_count
            
    sign = 1
    minus_count = 0 
    
     # Remove trailing commas and leading and trailing quotes (single and double) 
    num_str = num_str.rstrip(',').strip('"').strip("'")
        
    # Pre-check if any stripping or processing of valid characters is needed. 
    # Peel potentially nested [] and () around a number, leading +, and trailing * asterisks, then count up all valid minus signs encountered. 
    if VALID_CHAR_RE.search(num_str):        
        prev_length = -1
        while len(num_str) != prev_length:
            prev_length = len(num_str)
            num_str = num_str.rstrip('*])').lstrip('([')
            if num_str.startswith('-'):
                minus_count += 1        # log the - occurrence.
                num_str = num_str[1:]  # Remove a leading '-'
            if num_str.startswith('$'):  
                num_str = num_str[1:]  # Remove a leading '$'           
            if num_str.startswith('+'):
                num_str = num_str[1:]  # Remove a leading '+'   
                                    
        # Handle negative numbers 
        if minus_count == 1: 
            sign = -1        
        elif minus_count > 1:    # multiple negation creates an invalid/ambiguous number; we're not doing arithmetic, just removing plausibly neutral characters from numbers.
            return None             # there may still be minuses (dashes) embedded in numbers. The final Decimal()  digestion will catch those. 
            
    #end of VALID_CHAR processing.         
    
            
    # Check if the total length might exceed our precision capability (early out.) 
    if len(num_str) > ( MAX_PRECISION + 1 ):
        # Check if the length of the number string exceeds athe current precision.
        clean_num_str = NON_NUMERIC_RE.sub("", num_str)   # Remove all non-numeric characters    
        if len(clean_num_str) > MAX_PRECISION:
            skipped_due_to_precision += 1  
            return None  # Skip this number as it exceeds our precision
    
    # Handle decimal points and trailing .--- of any count.   
    #  Very specific.  100--  is seen as too ambiguous,  but 23.--   and  100.0--  and 555.   are valid.  
    dot_count = num_str.count('.')    
    
    # Multiple decimal dots are disqualifying. but Decimal() takes care of that.
    
    if( dot_count == 0  and num_str.endswith('-')):
        return None #  Invalid number e.g. " 17- "
    
    if (dot_count == 1 and num_str.endswith('-')):
        num_str = num_str.rstrip('-')  + "0"   # Numbers like 7.-- become 7.0 
            
    #Handle commas
    if "," in num_str:
        if not COMMA_NUM_RE.match(num_str):   # validate proper thousands separators. 
            return None                                        # Incorrect number format.
        num_str = num_str.replace(",", "")   # We have to remove the proper separator commas because Decimal doesn't allow them. 
        
    
    try:
        return sign * Decimal(num_str)
    except InvalidOperation:
        # conversion_fail_count += 1
        # print("Failed to convert: {}".format(num_str))   # Extra logging. Development only. 
        return None


# Main code

with localcontext() as ctx:

    ctx.prec = MAX_PRECISION
    if DO_PROFILING:
        start_time = time.time()     #  For profiling purposes.
    line_number = 0         
    grand_total = ZERO_DECIMAL
    numbers_found = False
    negative_numbers_count = 0
    unparsed_strings_found = False
    precision_exceeded = False
    result = ''
    
    get_selections = editor.getSelections()
    
    for sel in range(get_selections):
        start_pos = editor.getSelectionNStart(sel)
        end_pos = editor.getSelectionNEnd(sel)
        text = editor.getTextRange(start_pos, end_pos).strip()
        lines = text.split('\n')
        
        for line in lines:
            line_number  += 1                        
            numbers = line.split()
            
            for num in numbers:                        
                if ANY_ALPHA_RE.search(num):       # Skip this string as it contains invalid characters (letters of the alphabet). Won't be a simple unambiguous number.                       
                    continue      
                if not DIGIT_RE.search(num):         # Skip this string as it contains no decimal digits.   
                    continue
                if ANY_DISQUALIFIER_RE.search(num):    #ignore all numbers with disqualifying ambiguous characters.
                    continue     
                    
                parsed_num = parse_number(num)   # The real work. Returns a Decimal type (arbitrary precision.)
                
                if parsed_num is None:
                    unparsed_strings_found = True  # Flag if problematic string encountered which wasn't successfully parsed into a number. 
                    continue                
                                    
                grand_total += parsed_num           # The actual addition. In Decimal type format. 
                numbers_found = True
                
                if parsed_num < 0:
                    negative_numbers_count += 1                
                
#            # Check for infinity? - no longer needed as we avoid scientific notation, for now.  Some overflows could still be possible. 
#            if grand_total.is_infinite():


    try:                
        if numbers_found:
            if grand_total % 1 == 0:
                result = 'Selected Sum = {}'.format(int(grand_total))
            else:
                rounded_grand_total = grand_total.quantize(Decimal('0.00'))
                if rounded_grand_total == grand_total:
                    result = 'Selected Sum = {:.2f}'.format(grand_total)
                else:
                    result = 'Selected Sum = {}'.format(grand_total)
        else: 
            result = 'No selected valid numbers were found.'
            
    except InvalidOperation as e:
        result = "An error occurred on line {}: {}".format(line_number, str(e))   
     # Sometimes enough borderline large numbers are accepted and added that they overflow the digit limit. 
    
    if DO_PROFILING:
        elapsed_time = (time.time() - start_time) * 1000   # Convert to milliseconds. For profiling purposes.     
    
    notepad.messageBox(result, '')         
    copy_to_clipboard(result)
        
    if negative_numbers_count > 0:
        notepad.messageBox('Note: {} negative numbers were evaluated and subtracted.'.format(negative_numbers_count))
 
    if skipped_due_to_precision > 0:
        notepad.messageBox('{} numbers ignored due to digit length exceeding {}'.format(skipped_due_to_precision, ctx.prec), '')
    
    if DO_PROFILING:
        notepad.messageBox("Elapsed Time: {:.2f} ms".format(elapsed_time), "Performance Metrics")  # <-- Display elapsed time.  For profiling purposes.
        print("Elapsed Time: {:.2f} ms".format(elapsed_time))  # Extra logging. Development only. 
    
    
#    if conversion_fail_count > 0:
#        notepad.messageBox('{} numbers ignored due to conversion errors to arbitrary precision Decimal format.'.format(conversion_fail_count)) 
                
#    print(" {} numbers ignored due to conversion errors to Decimal arbitrary precision library format.".format(conversion_fail_count))     # Extra logging. Development only. 
    
#    if unparsed_strings_found:
#        notepad.messageBox('Warning: Special or problematic strings were encountered and ignored.', '')        
     
    
    
