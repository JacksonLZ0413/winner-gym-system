const app = getApp()

Page({
  data: {
    coaches: [],
    searchText: '',
    currentFilter: 'all',
    loading: false
  },

  onLoad: function () {
    this.loadCoaches()
  },

  onShow: function () {
    this.loadCoaches()
  },

  loadCoaches: function () {
    this.setData({ loading: true })
    app.request({
      url: '/coaches',
      noAuth: true
    }).then((data) => {
      this.setData({
        coaches: data,
        loading: false
      })
    }).catch(() => {
      this.setData({
        coaches: [],
        loading: false
      })
    })
  },

  onSearchInput: function (e) {
    this.setData({
      searchText: e.detail.value
    })
  },

  setFilter: function (e) {
    const filter = e.currentTarget.dataset.filter
    this.setData({
      currentFilter: filter
    })
  },

  goToDetail: function (e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/coach-detail/coach-detail?id=${id}`
    })
  }
})