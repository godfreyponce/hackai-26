import sys
import unittest
sys.path.append("/Users/advaith/Downloads/frontend hackai -26/advisorai/backend")
from services.transcript_parser import TranscriptParser

class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = TranscriptParser()

    def test_basic_transcript(self):
        text = """
Name: Jane Doe
Student ID: 123456789
Date: 2024-02-04: Computer Science Major CIP: 11.0101

Beginning of Undergraduate Record

2024 Fall
CS 1200 INTRO TO COMP SCI & SOFTWARE 2.000 2.000 A+ 8.000
CS 1337 COMPUTER SCIENCE I      3.000 3.000 B- 8.000
MATH 2413 DIFFERENTIAL CALCULUS 4.000 4.000 CR 0.000
CS 2305 DISCRETE MATHEMATICS I  3.000 0.000 0.000

Cum GPA: 3.500
Cum Totals 12.000 9.000 3.500 24.000
"""
        res = self.parser.parse_text(text)
        self.assertEqual(res.student_name, "Jane Doe")
        self.assertEqual(res.gpa, 3.5)
        self.assertEqual(res.major, "Computer Science")
        self.assertEqual(len(res.completed_courses), 4)

        cs1200 = res.completed_courses[0]
        self.assertEqual(cs1200.course_code, "CS 1200")
        self.assertEqual(cs1200.grade, "A+")
        
        m_2413 = res.completed_courses[2]
        self.assertEqual(m_2413.course_code, "MATH 2413")
        self.assertEqual(m_2413.grade, "CR")

        in_prog = res.completed_courses[3]
        self.assertEqual(in_prog.grade, "IP")
        
    def test_edge_cases(self):
        text = """
Name: Alice Smith
Program: Computer Science, BS

2024 Spring
CS 4349 ADVANCED ALGORITHM ANALYSIS 3.000 3.000 A 12.000
CS 1200 INTRO 2.000 2.000 W 0.000
Transfer Credit
2023 Fall
CS 1136 COMPUTER SCIENCE LAB 1.000 1.000 CR 0.000

Combined Cum GPA 3.850 Comb Totals 89.000 74.000 3.800
"""
        res = self.parser.parse_text(text)
        self.assertEqual(res.major, "Computer Science, BS")
        self.assertEqual(res.total_credit_hours, 74.0)

if __name__ == "__main__":
    unittest.main()
