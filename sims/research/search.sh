#!/bin/bash
# flat search; output TSV: query, id, views, duration, channel, channel_id, title
qs=(
"satisfying soft body simulation"
"soft body squish blender shorts"
"0% vs 100% softness simulation"
"soft body through grid simulation"
"satisfying cloth simulation blender"
"satisfying fluid simulation 3d"
"satisfying rigid body destruction blender"
"satisfying marble run 3d animation"
"satisfying 3d animation shorts"
"oddly satisfying 3d simulation"
"blender physics simulation satisfying shorts"
"satisfying slime simulation 3d"
"soft body vs hydraulic press 3d"
"satisfying balls simulation 3d"
"satisfying sand simulation 3d"
"satisfying jelly simulation"
"satisfying perfect fit 3d animation"
"satisfying cutting simulation 3d"
"satisfying gears 3d animation loop"
"satisfying color sorting 3d animation"
"satisfying glass breaking simulation"
"houdini satisfying simulation shorts"
"cinema 4d satisfying simulation"
"3d asmr animation shorts"
"satisfying domino 3d animation"
"satisfying spheres falling stairs 3d"
"soft body car crash simulation"
"satisfying balloon popping simulation 3d"
"satisfying funnel simulation"
"satisfying tetris 3d animation"
)
for q in "${qs[@]}"; do
  yt-dlp --flat-playlist --no-warnings --print "$q	%(id)s	%(view_count)s	%(duration)s	%(channel)s	%(channel_id)s	%(title)s" \
    "https://www.youtube.com/results?search_query=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$q")&sp=EgIYAQ%253D%253D" --playlist-end 80 2>/dev/null
done
