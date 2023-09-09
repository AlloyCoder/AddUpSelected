# AddUpSelected 
A single-file python script for Notepad++ which adds up all numbers in a selection.  Flexible and tolerant of various common formattings.

 
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
