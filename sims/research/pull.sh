while IFS=$'\t' read cid name; do
  yt-dlp --flat-playlist --no-warnings --playlist-end 400 --print "$name	%(id)s	%(view_count)s	%(title)s" "https://www.youtube.com/channel/$cid/shorts" 2>/dev/null &
  while [ $(jobs -r | wc -l) -ge 6 ]; do sleep 1; done
done < chan_list.tsv
wait
