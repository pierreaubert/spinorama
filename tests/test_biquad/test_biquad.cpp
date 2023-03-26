#include <cstdio>
#include "biquad.hpp"

int main()
{
    const int srates[] = {44100, 48000, 96000};
    const float freqs[] = {70, 80, 90, 100, 110, 120, 130};
    const float gains[] = {-3, 3, -1, 1};
    const float qs[] = {0.1, 1, 2, 5};
    const BiQuad::Type types[] = {
        BiQuad::LOW_PASS,
        BiQuad::HIGH_PASS,
        BiQuad::BAND_PASS,
        BiQuad::PEAKING,
        BiQuad::NOTCH,
        BiQuad::LOW_SHELF,
        BiQuad::HIGH_SHELF
    };

    for( auto srate : srates)
    {
        for( auto type : types)
        {
            for( auto gain : gains)
            {
                for( auto q : qs)
                {
                    auto q2 = q;
                    auto gain2 = gain;
                    if (type == BiQuad::NOTCH)
                    {
                        q2 = 30;
                        gain2 = 1.0;
                    }
                    if (type == BiQuad::LOW_SHELF || type == BiQuad::HIGH_SHELF)
                    {
                        q2 = 1/sqrt(2);
                    }
                    BiQuad bq = BiQuad(type, gain2, 100, srate, q2, false);
                    for( auto f : freqs)
                    {
                        auto computed = bq.gainAt(f, srate);
                        if (std::abs(computed) < 0.00001)
                        {
                            computed = 0.0;
                        }
                        printf("%+.5f srate=%5d q=%1.1f\n", computed, srate, q);
                    }
                }
            }
        }
    }
}
