// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
