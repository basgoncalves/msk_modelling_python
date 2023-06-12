import unittest
def my_fun():
        return 3

class test_bops(unittest.TestCase):
       
    def test_function(self):
        # Test 1
        self.assertEqual(my_fun(), 'a')
        
        
        # Test 2
        assert len([1, 2, 3]) == 3
        
        
            
        
if __name__ == '__main__':
    # Call the test function
    unittest.main()
