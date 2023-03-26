g++ -o test_biquad -I. test_biquad.cpp biquad.cpp
./test_biquad         > test_biquad.cpp.txt
python test_biquad.py
