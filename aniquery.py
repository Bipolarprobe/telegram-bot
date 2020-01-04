import requests

# TODO refactor recommend function defaults
def recommend(season="FALL", year=2019, minscore=70):
    # AniList database query through GraphQL
    # data query returns data in the structure requested
    query = """
    query SeasonalRecommend ($season: MediaSeason, $seasonYear: Int, $averageScore_greater: Int) {
      Page(page: 1, perPage: 20) {
        media (season: $season, seasonYear: $seasonYear, averageScore_greater: $averageScore_greater, type: ANIME) {
          id
          title {
            romaji
            english
          }
          averageScore
          duration
        }
      }
    }
    """
    # variables are stored in dict rather than passing via string formatting
    variables = {"season": season, "seasonYear": year, "averageScore_greater": minscore}
    
    url = "https://graphql.anilist.co"
    
    json = {"query": query, "variables": variables}
    
    response = requests.post(url, json=json)
    
    if response.ok:
        # response is returned as json for unpacking
        return response.json()
    else:
        return None

